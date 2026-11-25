import datetime as dt

import pytest
from httpx import AsyncClient

from baja.models import PaymentMethod, Role, TransactionType, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

ENTRY = {
    "type": "expense",
    "amount": 1250.5,
    "payment_method": "cash",
    "category": "utilities",
    "concept": " cfe ",
    "date": "2026-11-05",
    "description": "monthly electricity bill",
}


@pytest.mark.parametrize("role", [Role.owner, Role.manager])
async def test_owners_and_managers_record_transactions(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture, role: Role
) -> None:
    property = await create_property(save_fixture)
    recorder = await create_user(save_fixture, role)
    await login(recorder)

    response = await client.post(
        "/v1/transactions/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert response.status_code == 201
    body = response.json()
    assert {
        k: body[k]
        for k in ("amount", "concept", "source", "affects_balance", "entered_by_id")
    } == {
        "amount": 1250.5,
        "concept": "cfe",
        "source": "web",
        "affects_balance": True,
        "entered_by_id": str(recorder.id),
    }
    assert (await client.get(f"/v1/transactions/{body['id']}")).json() == body


async def test_amounts_are_exact_to_the_cent(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)
    for amount in ("0.10", "0.20"):
        await client.post(
            "/v1/transactions/",
            json={**ENTRY, "property_id": str(property.id), "amount": amount},
        )

    balances = (await client.get("/v1/balances/")).json()

    assert balances[0]["balance"] == -0.3


@pytest.mark.parametrize("amount", [0, -5, "12.345"])
async def test_amounts_must_be_positive_cents(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    amount: object,
) -> None:
    property = await create_property(save_fixture)
    await login(user)

    response = await client.post(
        "/v1/transactions/",
        json={**ENTRY, "property_id": str(property.id), "amount": amount},
    )

    assert response.status_code == 422


async def test_a_resent_entry_is_recorded_once(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)
    entry = {**ENTRY, "property_id": str(property.id), "external_id": "A1B2"}

    first = await client.post("/v1/transactions/", json=entry)
    second = await client.post("/v1/transactions/", json=entry)

    assert second.status_code == 201
    assert second.json() == first.json()
    listed = (await client.get("/v1/transactions/")).json()
    assert listed["pagination"]["total_count"] == 1


async def test_a_resent_entry_after_deleting_it_is_refused(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)
    entry = {**ENTRY, "property_id": str(property.id), "external_id": "A1B2"}
    first = await client.post("/v1/transactions/", json=entry)
    await client.delete(f"/v1/transactions/{first.json()['id']}")

    response = await client.post("/v1/transactions/", json=entry)

    assert (response.status_code, response.json()["error"]) == (
        409,
        "TransactionDeleted",
    )


async def test_archived_properties_take_no_new_transactions(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture, is_archived=True)
    await login(user)

    response = await client.post(
        "/v1/transactions/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert (response.status_code, response.json()["error"]) == (
        409,
        "PropertyArchived",
    )


async def test_unknown_properties_are_not_found(
    client: AsyncClient, login: LoginFixture, user: User
) -> None:
    await login(user)

    response = await client.post(
        "/v1/transactions/",
        json={**ENTRY, "property_id": "0190d7f2-0000-7000-8000-000000000000"},
    )

    assert response.status_code == 404


async def test_homeowners_cannot_record(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, property)
    await login(homeowner)

    response = await client.post(
        "/v1/transactions/", json={**ENTRY, "property_id": str(property.id)}
    )

    assert (response.status_code, response.json()["detail"]) == (
        403,
        "Only owners and managers can record transactions.",
    )


async def test_homeowners_see_only_their_properties(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    own = await create_transaction(save_fixture, mine)
    other = await create_transaction(save_fixture, theirs)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    listed = (await client.get("/v1/transactions/")).json()
    hidden = await client.get(f"/v1/transactions/{other.id}")
    balances = (await client.get("/v1/balances/")).json()

    assert [t["id"] for t in listed["items"]] == [str(own.id)]
    assert hidden.status_code == 404
    assert [b["property_name"] for b in balances] == ["Campo 9"]


async def test_list_filters_and_pages_newest_first(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    for day in (3, 1, 2):
        await create_transaction(
            save_fixture, campo, date=dt.date(2026, 11, day), concept=f"day {day}"
        )
    await create_transaction(save_fixture, campo, type=TransactionType.income)
    await create_transaction(save_fixture, colinas)
    await login(user)

    response = await client.get(
        "/v1/transactions/",
        params={
            "property_id": str(campo.id),
            "type": "expense",
            "category": "UTILITIES",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "limit": 1,
        },
    )

    body = response.json()
    assert [t["concept"] for t in body["items"]] == ["day 3"]
    assert body["pagination"] == {"total_count": 2, "max_page": 2}


async def test_deleted_transactions_disappear_and_stop_counting(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    transaction = await create_transaction(save_fixture, property, amount="500")
    await login(user)

    response = await client.delete(f"/v1/transactions/{transaction.id}")

    assert response.status_code == 204
    assert (await client.get(f"/v1/transactions/{transaction.id}")).status_code == 404
    assert (await client.get("/v1/balances/")).json()[0]["balance"] == 0


async def test_update_corrects_an_entry(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    transaction = await create_transaction(save_fixture, property, description="typo")
    await login(user)

    response = await client.patch(
        f"/v1/transactions/{transaction.id}",
        json={"amount": "99.90", "description": None, "category": None},
    )

    body = response.json()
    assert (body["amount"], body["description"], body["category"]) == (
        99.9,
        None,
        "utilities",
    )


async def test_homeowners_cannot_change_transactions(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    transaction = await create_transaction(save_fixture, property)
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, property)
    await login(homeowner)

    patched = await client.patch(
        f"/v1/transactions/{transaction.id}", json={"amount": "1"}
    )
    deleted = await client.delete(f"/v1/transactions/{transaction.id}")

    assert (patched.status_code, deleted.status_code) == (403, 403)


async def test_anonymous_callers_see_nothing(client: AsyncClient) -> None:
    assert (await client.get("/v1/transactions/")).status_code == 401
    assert (await client.get("/v1/balances/")).status_code == 401


async def test_payment_method_is_required(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)
    entry = {**ENTRY, "property_id": str(property.id)}
    del entry["payment_method"]

    response = await client.post("/v1/transactions/", json=entry)

    assert response.status_code == 422


async def test_unknown_payment_methods_are_refused(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await login(user)

    response = await client.post(
        "/v1/transactions/",
        json={**ENTRY, "property_id": str(property.id), "payment_method": "bitcoin"},
    )

    assert response.status_code == 422
    assert PaymentMethod.cash in response.text


async def test_the_summary_adds_up_what_the_filters_list(
    client: AsyncClient, login: LoginFixture, save_fixture: SaveFixture
) -> None:
    mine = await create_property(save_fixture, name="Campo 9")
    theirs = await create_property(save_fixture, name="Colinas 21")
    for property, type, amount, day in [
        (mine, TransactionType.income, "1000", 1),
        (mine, TransactionType.expense, "250.50", 2),
        (mine, TransactionType.expense, "100", 20),
        (theirs, TransactionType.expense, "999", 2),
    ]:
        await create_transaction(
            save_fixture,
            property,
            type=type,
            amount=amount,
            date=dt.date(2026, 11, day),
        )
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, mine)
    await login(homeowner)

    everything = await client.get("/v1/transactions/summary")
    early = await client.get(
        "/v1/transactions/summary", params={"end_date": "2026-11-10", "limit": 1}
    )

    assert everything.json() == {
        "count": 3,
        "income_total": 1000.0,
        "expense_total": 350.5,
    }
    assert early.json() == {"count": 2, "income_total": 1000.0, "expense_total": 250.5}
