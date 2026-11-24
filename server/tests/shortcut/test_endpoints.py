from collections.abc import Awaitable, Callable
from typing import Any

import pytest
from httpx import AsyncClient, Response

from baja.auth.service import auth as auth_service
from baja.kit.db.postgres import AsyncSession
from baja.models import Role, TransactionType, User
from tests.fixtures import (
    SaveFixture,
    assign_properties,
    create_property,
    create_transaction,
    create_user,
)

type Phone = Callable[..., Awaitable[Response]]

EXPENSE = {
    "external_id": "8F14E45F-CEEA-467A-9575-0F0E0F0E0F0E",
    "amount": 20880,
    "date": "2026-11-05",
    "type": "Expense",
    "method": "Credit Card",
    "concept": " Carpentry Palma ",
    "category": "Maintenance/Projects",
    "description": "Final payment doors\n",
    "addresses": ["Parque 31"],
}


@pytest.fixture
async def phone(client: AsyncClient, session: AsyncSession, user: User) -> Phone:
    """Calls the API as the Shortcut does: with a bearer token."""
    token, _ = await auth_service.issue_api_token(session, user, label="iPhone")

    async def call(method: str, path: str, **kwargs: Any) -> Response:
        return await client.request(
            method,
            f"/v1/shortcut{path}",
            headers={"Authorization": f"Bearer {token}\n"},
            **kwargs,
        )

    return call


async def transactions(client: AsyncClient, phone: Phone) -> list[dict[str, Any]]:
    # The token works on the whole API, not only the Shortcut's endpoints.
    response = await phone("GET", "/../transactions/")
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def test_records_an_expense_as_the_old_intake_did(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture, user: User
) -> None:
    parque = await create_property(save_fixture, name="Parque 31")

    response = await phone("POST", "/expenses", json=EXPENSE)

    assert response.status_code == 200
    assert response.json() == {
        "inserted": 1,
        "title": "$20,880.00 · Parque 31",
        "summary": "Carpentry palma · Credit Card · 05 Nov",
    }
    [recorded] = await transactions(client, phone)
    assert {k: recorded[k] for k in recorded if k not in {"id", "created_at"}} == {
        "property_id": str(parque.id),
        "type": "expense",
        "amount": 20880.0,
        "payment_method": "credit card",
        "category": "maintenance/projects",
        "concept": "carpentry palma",
        "date": "2026-11-05",
        "description": "final payment doors",
        "source": "shortcut",
        "external_id": EXPENSE["external_id"],
        "affects_balance": False,
        "entered_by_id": str(user.id),
    }


async def test_a_resend_says_already_saved(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")
    await phone("POST", "/expenses", json=EXPENSE)

    response = await phone("POST", "/expenses", json=EXPENSE)

    assert response.json()["inserted"] == 0
    assert response.json()["title"] == "Already saved · $20,880.00"
    assert len(await transactions(client, phone)) == 1


async def test_one_entry_for_several_villas_charges_each_in_full(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    for name in ("Parque 31", "Campo 9"):
        await create_property(save_fixture, name=name)
    entry = {**EXPENSE, "amount": "1500.5", "addresses": [["parque 31\nCampo 9"]]}

    response = await phone("POST", "/expenses", json=entry)

    assert response.json() == {
        "inserted": 2,
        "title": "$1,500.50 each · 2 villas",
        "summary": "Parque 31 · Campo 9\nCarpentry palma · Credit Card · 05 Nov",
    }
    recorded = await transactions(client, phone)
    assert sorted(t["external_id"] for t in recorded) == [
        f"{EXPENSE['external_id']}-1",
        f"{EXPENSE['external_id']}-2",
    ]
    assert {t["amount"] for t in recorded} == {1500.5}


async def test_an_unknown_villa_saves_nothing(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")
    entry = {**EXPENSE, "addresses": ["Parque 31", "Atlantis"]}

    response = await phone("POST", "/expenses", json=entry)

    assert (response.status_code, response.json()["detail"]) == (
        400,
        "No villa named 'Atlantis'.",
    )
    assert await transactions(client, phone) == []


async def test_no_villa_is_refused(phone: Phone) -> None:
    response = await phone("POST", "/expenses", json={**EXPENSE, "addresses": []})

    assert (response.status_code, response.json()["detail"]) == (
        400,
        "No villa selected.",
    )


async def test_income_is_always_a_cash_deposit(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")
    entry = {
        **EXPENSE,
        "type": "Income",
        "method": "Credit Card",
        "category": "",
        "concept": "",
    }

    response = await phone("POST", "/expenses", json=entry)

    assert response.json()["summary"] == "Deposit · 05 Nov"
    [recorded] = await transactions(client, phone)
    assert (
        recorded["type"],
        recorded["payment_method"],
        recorded["category"],
        recorded["concept"],
        recorded["affects_balance"],
    ) == ("income", "cash", "income", "deposit", True)


async def test_guest_expenses_go_to_their_own_list(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")
    entry = {**EXPENSE, "is_guest": True, "method": "", "category": "Transport"}

    response = await phone("POST", "/expenses", json=entry)

    assert response.json()["summary"] == "Carpentry palma · Guest · 05 Nov"
    guest = (await phone("GET", "/../guest-expenses/")).json()["items"]
    assert [(g["category"], g["source"]) for g in guest] == [("transport", "shortcut")]
    assert await transactions(client, phone) == []


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"method": ""}, "An expense needs method."),
        ({"concept": " ", "category": ""}, "An expense needs concept, category."),
        ({"method": "bitcoin"}, "Input should be"),
        ({"amount": 0.004}, "must be at least 0.01"),
    ],
)
async def test_incomplete_expenses_are_refused(
    phone: Phone, changes: dict[str, Any], message: str
) -> None:
    response = await phone("POST", "/expenses", json={**EXPENSE, **changes})

    assert response.status_code == 422
    assert message in response.text


async def test_amounts_are_rounded_to_cents(
    phone: Phone, client: AsyncClient, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")

    await phone("POST", "/expenses", json={**EXPENSE, "amount": 99.995})

    [recorded] = await transactions(client, phone)
    assert recorded["amount"] == 100.0


async def test_archived_villas_are_not_offered_or_recorded(
    phone: Phone, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31", is_archived=True)
    await create_property(save_fixture, name="Campo 9")
    await create_property(save_fixture, name="colinas 21")

    villas = await phone("GET", "/villas")
    recorded = await phone("POST", "/expenses", json=EXPENSE)

    assert villas.json() == {"villas": ["Campo 9", "colinas 21"]}
    assert (recorded.status_code, recorded.json()["error"]) == (
        409,
        "PropertyArchived",
    )


async def test_categories_are_the_ones_in_use_most_used_first(
    phone: Phone, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    for category in ("staff", "utilities", "utilities", "other", "utilities"):
        await create_transaction(save_fixture, property, category=category)
    await create_transaction(save_fixture, property, category="staff")
    await create_transaction(
        save_fixture, property, type=TransactionType.income, category="income"
    )

    expense = await phone("GET", "/categories")
    income = await phone("GET", "/categories", params={"type": "income"})

    assert expense.json() == {"categories": ["utilities", "staff", "other"]}
    assert income.json() == {"categories": ["income"]}


async def test_homeowners_cannot_use_the_shortcut(
    client: AsyncClient, session: AsyncSession, save_fixture: SaveFixture
) -> None:
    parque = await create_property(save_fixture, name="Parque 31")
    homeowner = await create_user(save_fixture, Role.homeowner)
    await assign_properties(save_fixture, homeowner, parque)
    token, _ = await auth_service.issue_api_token(session, homeowner, label="x")

    response = await client.post(
        "/v1/shortcut/expenses",
        json=EXPENSE,
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


async def test_without_a_token_nothing_is_served(client: AsyncClient) -> None:
    assert (await client.get("/v1/shortcut/villas")).status_code == 401


async def test_cash_expenses_come_out_of_the_balance(
    phone: Phone, save_fixture: SaveFixture
) -> None:
    await create_property(save_fixture, name="Parque 31")

    await phone("POST", "/expenses", json={**EXPENSE, "method": "cash"})

    balances = (await phone("GET", "/../balances/")).json()
    assert balances[0]["balance"] == -20880
