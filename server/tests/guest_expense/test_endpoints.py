import datetime as dt

import pytest
from httpx import AsyncClient

from baja.models import Company, Role, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_guest_expense,
    create_property,
    create_transaction,
    create_user,
)

ENTRY = {
    "amount": "1500.00",
    "category": "supermarket",
    "concept": " costco ",
    "date": "2026-11-05",
    "description": "groceries before arrival",
}


@pytest.mark.parametrize("role", [Role.owner, Role.manager])
async def test_owners_and_managers_record_guest_expenses(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture, role: Role
) -> None:
    property = await create_property(save_fixture)
    recorder = await create_user(save_fixture, role)
    await login(recorder)

    response = await client.post(
        "/v1/guest-expenses/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert (body["amount"], body["concept"], body["entered_by_id"]) == (
        1500.0,
        "costco",
        str(recorder.id),
    )
    assert (await client.get(f"/v1/guest-expenses/{body['id']}")).json() == body


async def test_guest_expenses_never_touch_the_balance(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await create_transaction(save_fixture, property, amount="100")
    await login(user)

    await client.post(
        "/v1/guest-expenses/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert (await client.get("/v1/balances/")).json()[0]["balance"] == -100
    assert (await client.get("/v1/transactions/")).json()["pagination"][
        "total_count"
    ] == 1


async def test_a_resent_entry_is_recorded_once(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)
    entry = {**ENTRY, "property_id": str(property.id), "external_id": "G1"}

    first = await client.post("/v1/guest-expenses/", json=entry)
    second = await client.post("/v1/guest-expenses/", json=entry)

    assert second.json() == first.json()
    listed = (await client.get("/v1/guest-expenses/")).json()
    assert listed["pagination"]["total_count"] == 1


async def test_archived_properties_take_no_new_guest_expenses(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture, is_archived=True)
    await login(user)

    response = await client.post(
        "/v1/guest-expenses/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert (response.status_code, response.json()["error"]) == (
        409,
        "PropertyArchived",
    )


async def test_homeowners_read_only_their_properties(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    own = await create_guest_expense(save_fixture, mine)
    other = await create_guest_expense(save_fixture, theirs)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    listed = (await client.get("/v1/guest-expenses/")).json()
    hidden = await client.get(f"/v1/guest-expenses/{other.id}")
    created = await client.post(
        "/v1/guest-expenses/", json={**ENTRY, "property_id": str(mine.id)}
    )

    assert [g["id"] for g in listed["items"]] == [str(own.id)]
    assert (hidden.status_code, created.status_code) == (404, 403)


async def test_list_filters_newest_first(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    for day in (1, 3, 2):
        await create_guest_expense(
            save_fixture, campo, date=dt.date(2026, 11, day), concept=f"day {day}"
        )
    await create_guest_expense(save_fixture, campo, category="services")
    await create_guest_expense(save_fixture, colinas)
    await login(user)

    response = await client.get(
        "/v1/guest-expenses/",
        params={
            "property_id": str(campo.id),
            "category": "Transport",
            "start_date": "2026-11-02",
        },
    )

    assert [g["concept"] for g in response.json()["items"]] == ["day 3", "day 2"]


async def test_update_and_delete(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    guest_expense = await create_guest_expense(save_fixture, property)
    await login(user)

    patched = await client.patch(
        f"/v1/guest-expenses/{guest_expense.id}",
        json={"amount": "500.25", "concept": None},
    )
    deleted = await client.delete(f"/v1/guest-expenses/{guest_expense.id}")
    after = await client.get(f"/v1/guest-expenses/{guest_expense.id}")

    assert (patched.json()["amount"], patched.json()["concept"]) == (
        500.25,
        "airport pickup",
    )
    assert (deleted.status_code, after.status_code) == (204, 404)


async def test_moving_to_an_archived_property_is_refused(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    sold = await create_property(save_fixture, name="Sold", is_archived=True)
    guest_expense = await create_guest_expense(save_fixture, campo)
    await login(user)

    response = await client.patch(
        f"/v1/guest-expenses/{guest_expense.id}",
        json={"property_id": str(sold.id)},
    )

    assert response.status_code == 409


async def test_the_summary_adds_up_and_says_what_is_billed(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    company: Company,
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    billed = await create_guest_expense(
        save_fixture, campo, amount="1000", date=dt.date(2026, 11, 2)
    )
    await create_guest_expense(
        save_fixture, campo, amount="250.50", date=dt.date(2026, 11, 3)
    )
    await create_guest_expense(
        save_fixture, colinas, amount="99", date=dt.date(2026, 11, 4)
    )
    await login(user)
    await client.post(
        "/v1/invoices/",
        json={
            "property_id": str(campo.id),
            "recipient_name": "Ana Guest",
            "email": "ana@example.com",
            "issued_on": "2026-11-25",
            "due_on": "2026-11-30",
            "lines": [
                {
                    "description": "x",
                    "unit_price": "1000",
                    "guest_expense_id": str(billed.id),
                }
            ],
        },
    )

    campo_only = await client.get(
        "/v1/guest-expenses/summary", params={"property_id": str(campo.id)}
    )
    open_ = await client.get("/v1/guest-expenses/summary", params={"invoiced": "false"})

    assert campo_only.json() == {"count": 2, "total": 1250.5, "billed_total": 1000.0}
    assert open_.json() == {"count": 2, "total": 349.5, "billed_total": 0.0}
