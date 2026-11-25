import datetime as dt
import io

from httpx import AsyncClient
from openpyxl import load_workbook
from pypdf import PdfReader

from baja.models import Company, Property, Role, TransactionType, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

PERIOD = {"start": "2026-10-15", "end": "2026-12-31"}


async def bills(save_fixture: SaveFixture, property: Property) -> None:
    for day, concept, amount in [
        (dt.date(2026, 10, 20), "Pool creations", "5500"),
        (dt.date(2026, 10, 1), "pool creations", "999"),  # before the period
        (dt.date(2026, 10, 21), "CFE", "1200"),
        (dt.date(2026, 10, 22), "cfe bill", "1"),  # not exactly "cfe"
        (dt.date(2026, 12, 3), "telmex internet", "899"),
        (dt.date(2026, 12, 4), "starlink", "1305"),
        (dt.date(2026, 12, 5), "pool water", "300"),  # pool comes first
        (dt.date(2026, 12, 6), "housekeeping", "5000"),
        (dt.date(2026, 12, 7), "costco", "700"),  # no bucket
    ]:
        await create_transaction(
            save_fixture, property, date=day, concept=concept, amount=amount
        )
    await create_transaction(
        save_fixture,
        property,
        date=dt.date(2026, 12, 8),
        concept="pool refund",
        type=TransactionType.income,
    )


async def test_bills_by_month_counted_once(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await bills(save_fixture, campo)
    await login(user)

    response = await client.get(
        "/v1/reports/utilities",
        params={
            **PERIOD,
            "property_id": str(campo.id),
            "buckets": ["pool", "cfe", "internet"],
        },
    )

    body = response.json()
    assert body["property_name"] == "Campo 9"
    assert [b["key"] for b in body["buckets"]] == ["pool", "cfe", "internet"]
    assert [
        (
            m["month"],
            {k: (v["total"], v["count"]) for k, v in m["buckets"].items()},
            m["total"],
        )
        for m in body["months"]
    ] == [
        ("2026-10", {"pool": (5500, 1), "cfe": (1200, 1), "internet": (0, 0)}, 6700),
        ("2026-11", {"pool": (0, 0), "cfe": (0, 0), "internet": (0, 0)}, 0),
        ("2026-12", {"pool": (300, 1), "cfe": (0, 0), "internet": (2204, 2)}, 2504),
    ]
    assert body["totals"]["internet"] == {"total": 2204, "count": 2}
    assert body["grand_total"] == 9204


async def test_a_concept_goes_to_the_first_bucket_even_if_not_shown(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await bills(save_fixture, campo)
    await login(user)

    response = await client.get(
        "/v1/reports/utilities", params={**PERIOD, "buckets": ["water"]}
    )

    assert response.json()["totals"] == {"water": {"total": 0, "count": 0}}


async def test_utilities_by_default_and_the_tracker_on_request(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await bills(save_fixture, campo)
    await login(user)

    default = await client.get("/v1/reports/utilities", params=PERIOD)
    tracker = await client.get(
        "/v1/reports/utilities", params={**PERIOD, "buckets": ["housekeeping"]}
    )
    buckets = await client.get("/v1/reports/buckets")

    assert "housekeeping" not in default.json()["totals"]
    assert tracker.json()["totals"] == {"housekeeping": {"total": 5000, "count": 1}}
    assert [b["key"] for b in buckets.json()][-2:] == ["housekeeping", "staff"]


async def test_homeowners_see_only_their_properties_bills(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    await bills(save_fixture, mine)
    await bills(save_fixture, theirs)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    everything = await client.get("/v1/reports/utilities", params=PERIOD)
    other = await client.get(
        "/v1/reports/utilities", params={**PERIOD, "property_id": str(theirs.id)}
    )

    assert everything.json()["property_name"] is None
    assert everything.json()["totals"]["pool"] == {"total": 5800, "count": 2}
    assert other.status_code == 404


async def test_in_dollars(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await bills(save_fixture, campo)
    await login(user)

    response = await client.get(
        "/v1/reports/utilities",
        params={**PERIOD, "buckets": ["pool"], "currency": "USD"},
    )

    body = response.json()
    assert [m["buckets"]["pool"]["total"] for m in body["months"]] == [333.33, 0, 18.18]
    assert body["grand_total"] == 351.51


async def test_unknown_buckets_are_refused(
    client: AsyncClient, login: LoginFixture, user: User, company: Company
) -> None:
    await login(user)

    response = await client.get(
        "/v1/reports/utilities", params={**PERIOD, "buckets": ["pool", "spa"]}
    )

    assert response.status_code == 422
    assert response.json()["detail"].startswith("No such buckets: spa.")


async def test_pdf_and_spreadsheet(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await bills(save_fixture, campo)
    await login(user)

    pdf = await client.get("/v1/reports/utilities.pdf", params=PERIOD)
    xlsx = await client.get("/v1/reports/utilities.xlsx", params=PERIOD)

    assert pdf.headers["content-disposition"] == (
        'attachment; filename="utilities-2026-10-15-2026-12-31.pdf"'
    )
    text = PdfReader(io.BytesIO(pdf.content)).pages[0].extract_text()
    for expected in ("All properties", "Oct 2026", "Dec 2026", "5,500.00", "9,204.00"):
        assert expected in text
    sheet = load_workbook(io.BytesIO(xlsx.content)).active
    assert sheet is not None
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    assert rows[-1][0] == "Total"
    assert rows[-1][-1] == 9204
