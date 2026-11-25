import datetime as dt
import io

import pytest
from httpx import AsyncClient
from openpyxl import load_workbook
from pypdf import PdfReader

from baja.models import Company, PaymentMethod, Property, Role, TransactionType, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

INCOME = TransactionType.income
CASH, CARD = PaymentMethod.cash, PaymentMethod.credit_card
NOV = {"start": "2026-11-01", "end": "2026-11-30"}


async def ledger(save_fixture: SaveFixture, property: Property) -> None:
    """Campo 9 in November, with what came before and after it."""
    for day, type, method, amount, category in [
        (dt.date(2026, 10, 20), INCOME, CASH, "1000", "income"),
        (dt.date(2026, 10, 25), TransactionType.expense, CASH, "200", "staff"),
        (dt.date(2026, 11, 2), TransactionType.expense, CARD, "3000", "utilities"),
        (dt.date(2026, 11, 5), INCOME, PaymentMethod.wire, "500", "income"),
        (dt.date(2026, 11, 10), TransactionType.expense, CASH, "850", "staff"),
        (dt.date(2026, 11, 12), TransactionType.expense, CASH, "50.50", "utilities"),
        (dt.date(2026, 12, 1), TransactionType.expense, CASH, "999", "staff"),
    ]:
        await create_transaction(
            save_fixture,
            property,
            date=day,
            type=type,
            payment_method=method,
            amount=amount,
            category=category,
            concept=f"{category} {day.day}",
        )


async def test_the_statement_tells_the_balances_story(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await ledger(save_fixture, campo)
    await create_transaction(
        save_fixture, await create_property(save_fixture, name="Other")
    )
    await login(user)

    response = await client.get(f"/v1/properties/{campo.id}/statement", params=NOV)

    body = response.json()
    assert {
        k: body[k]
        for k in (
            "property_name",
            "currency",
            "exchange_rate",
            "opening_balance",
            "closing_balance",
            "income_total",
            "expense_total",
            "balance_expense_total",
        )
    } == {
        "property_name": "Campo 9",
        "currency": "MXN",
        "exchange_rate": None,
        "opening_balance": 800.0,
        "closing_balance": 399.5,
        "income_total": 500.0,
        "expense_total": 3900.5,
        "balance_expense_total": 900.5,
    }
    assert [(e["concept"], e["balance_after"]) for e in body["entries"]] == [
        ("utilities 2", 800.0),
        ("income 5", 1300.0),
        ("staff 10", 450.0),
        ("utilities 12", 399.5),
    ]
    assert body["expenses_by_method"] == [
        {"payment_method": "credit card", "total": 3000.0},
        {"payment_method": "cash", "total": 900.5},
    ]
    assert [
        (c["category"], c["total"], [e["concept"] for e in c["entries"]])
        for c in body["expenses_by_category"]
    ] == [
        ("utilities", 3050.5, ["utilities 2", "utilities 12"]),
        ("staff", 850.0, ["staff 10"]),
    ]


async def test_in_dollars_every_figure_adds_up(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await ledger(save_fixture, campo)
    await login(user)

    response = await client.get(
        f"/v1/properties/{campo.id}/statement", params={**NOV, "currency": "USD"}
    )

    body = response.json()
    assert (body["currency"], body["exchange_rate"]) == ("USD", "16.5000")
    # 800 / 16.5 = 48.48; each entry is converted, then everything is summed.
    assert [e["amount"] for e in body["entries"]] == [181.82, 30.3, 51.52, 3.06]
    assert body["opening_balance"] == 48.48
    assert body["closing_balance"] == round(48.48 + 30.3 - 51.52 - 3.06, 2)
    assert body["expense_total"] == round(181.82 + 51.52 + 3.06, 2)


async def test_an_empty_period_still_has_its_balances(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await ledger(save_fixture, campo)
    await login(user)

    response = await client.get(
        f"/v1/properties/{campo.id}/statement",
        params={"start": "2026-11-13", "end": "2026-11-30"},
    )

    body = response.json()
    assert (body["opening_balance"], body["closing_balance"], body["entries"]) == (
        399.5,
        399.5,
        [],
    )


async def test_a_period_must_not_end_before_it_starts(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    response = await client.get(
        f"/v1/properties/{campo.id}/statement",
        params={"start": "2026-11-30", "end": "2026-11-01"},
    )

    assert (response.status_code, response.json()["error"]) == (422, "PeriodInvalid")


async def test_homeowners_get_only_their_own(
    client: AsyncClient,
    login: LoginFixture,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    own = await client.get(f"/v1/properties/{mine.id}/statement", params=NOV)
    other = await client.get(f"/v1/properties/{theirs.id}/statement.pdf", params=NOV)

    assert (own.status_code, other.status_code) == (200, 404)


async def test_the_pdf_is_the_statement_on_paper(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await ledger(save_fixture, campo)
    await login(user)

    response = await client.get(f"/v1/properties/{campo.id}/statement.pdf", params=NOV)

    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        'attachment; filename="campo-9-statement-2026-11-01-2026-11-30.pdf"'
    )
    text = PdfReader(io.BytesIO(response.content)).pages[0].extract_text()
    for expected in (
        "Baja Luxury Management",
        "Campo 9",
        "Nov 1, 2026 – Nov 30, 2026",
        "800.00",
        "-900.50",
        "399.50",
        "3,900.50",
        "Utilities 12",
        "Page 1 of 1",
    ):
        assert expected in text


async def test_the_pdf_runs_onto_more_pages(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture)
    for day in range(1, 31):
        for _ in range(3):
            await create_transaction(save_fixture, campo, date=dt.date(2026, 11, day))
    await login(user)

    response = await client.get(f"/v1/properties/{campo.id}/statement.pdf", params=NOV)

    pages = PdfReader(io.BytesIO(response.content)).pages
    assert len(pages) > 1
    last = pages[-1].extract_text()
    assert f"Page {len(pages)} of {len(pages)}" in last
    assert "Date" in last  # the column heads again


async def test_the_spreadsheet_has_real_numbers_and_dates(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    await ledger(save_fixture, campo)
    await login(user)

    response = await client.get(f"/v1/properties/{campo.id}/statement.xlsx", params=NOV)

    assert response.headers["content-disposition"].endswith(
        'statement-2026-11-01-2026-11-30.xlsx"'
    )
    sheet = load_workbook(io.BytesIO(response.content)).active
    assert sheet is not None
    rows = [list(row) for row in sheet.iter_rows(values_only=True)]
    head = rows.index(
        ["Date", "Description", "Concept", "Method", "Expense", "Income", "Balance"]
    )
    assert rows[head + 1][0] == dt.datetime(2026, 11, 2)
    assert rows[head + 1][2:] == ["Utilities 2", "Credit card", 3000, None, 800]
    assert rows[-1] == ["Total", None, None, None, 3900.5, 500, 399.5]
    assert ["Previous balance", 800] in [row[:2] for row in rows]


async def test_without_a_company_there_is_no_statement(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture)
    await login(user)

    response = await client.get(f"/v1/properties/{campo.id}/statement", params=NOV)

    assert (response.status_code, response.json()["error"]) == (503, "CompanyNotSetUp")


@pytest.mark.parametrize("suffix", ["", ".pdf", ".xlsx"])
async def test_anonymous_callers_get_nothing(
    client: AsyncClient, save_fixture: SaveFixture, suffix: str
) -> None:
    campo = await create_property(save_fixture)

    response = await client.get(
        f"/v1/properties/{campo.id}/statement{suffix}", params=NOV
    )

    assert response.status_code == 401
