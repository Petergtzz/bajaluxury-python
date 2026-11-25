import datetime as dt

import pytest
from httpx import AsyncClient

from baja.models import PaymentMethod, TransactionType, User
from tests.fixtures import (
    LoginFixture,
    SaveFixture,
    create_property,
    create_transaction,
)

CASH = PaymentMethod.cash
CARD = PaymentMethod.credit_card
DEBIT = PaymentMethod.debit_card
WITHDRAWAL = PaymentMethod.withdrawal


async def test_income_adds_and_cash_expenses_deduct(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    for type, method, amount in [
        (TransactionType.income, PaymentMethod.wire, "10000"),
        (TransactionType.expense, CASH, "2500.50"),
        (TransactionType.expense, CARD, "4000"),  # the owner's card
        (TransactionType.expense, DEBIT, "300"),
        (TransactionType.expense, PaymentMethod.check, "700"),
    ]:
        await create_transaction(
            save_fixture, property, type=type, payment_method=method, amount=amount
        )
    await login(user)

    balances = (await client.get("/v1/balances/")).json()

    assert balances[0]["balance"] == 7499.5


async def test_a_property_deducts_the_methods_it_names(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    soleil = await create_property(
        save_fixture, name="Soleil", balance_methods=[DEBIT, WITHDRAWAL]
    )
    for method, amount in [(CASH, "1000"), (DEBIT, "200"), (WITHDRAWAL, "30")]:
        await create_transaction(
            save_fixture, soleil, payment_method=method, amount=amount
        )
    await login(user)

    balances = (await client.get("/v1/balances/")).json()

    assert balances[0]["balance"] == -230


@pytest.mark.parametrize(
    ("change", "affects_balance"),
    [
        ({"payment_method": "credit card"}, False),
        ({"type": "income", "payment_method": "credit card"}, True),
        ({"amount": "5"}, True),
    ],
)
async def test_corrections_decide_the_balance_effect_again(
    client: AsyncClient,
    login: LoginFixture,
    user: User,
    save_fixture: SaveFixture,
    change: dict[str, str],
    affects_balance: bool,
) -> None:
    property = await create_property(save_fixture)
    transaction = await create_transaction(save_fixture, property)
    await login(user)

    response = await client.patch(f"/v1/transactions/{transaction.id}", json=change)

    assert response.json()["affects_balance"] is affects_balance


async def test_moving_to_another_property_uses_its_rule(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    soleil = await create_property(
        save_fixture, name="Soleil", balance_methods=[DEBIT, WITHDRAWAL]
    )
    transaction = await create_transaction(save_fixture, campo, payment_method=CASH)
    await login(user)

    response = await client.patch(
        f"/v1/transactions/{transaction.id}", json={"property_id": str(soleil.id)}
    )

    assert (response.json()["property_id"], response.json()["affects_balance"]) == (
        str(soleil.id),
        False,
    )


async def test_moving_to_an_archived_property_is_refused(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    sold = await create_property(save_fixture, name="Sold", is_archived=True)
    transaction = await create_transaction(save_fixture, campo)
    await login(user)

    response = await client.patch(
        f"/v1/transactions/{transaction.id}", json={"property_id": str(sold.id)}
    )

    assert response.status_code == 409


async def test_changing_the_rule_leaves_past_transactions_alone(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    property = await create_property(save_fixture)
    await create_transaction(save_fixture, property, payment_method=CASH, amount="80")
    await login(user)

    await client.patch(
        f"/v1/properties/{property.id}", json={"balance_methods": ["debit card"]}
    )
    await client.post(
        "/v1/transactions/",
        json={
            "property_id": str(property.id),
            "type": "expense",
            "amount": "20",
            "payment_method": "debit card",
            "category": "supermarket",
            "concept": "costco",
            "date": "2026-11-20",
        },
    )

    assert (await client.get("/v1/balances/")).json()[0]["balance"] == -100


async def test_balances_list_the_most_owed_first_with_last_dates(
    client: AsyncClient, login: LoginFixture, user: User, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    colinas = await create_property(save_fixture, name="Colinas 21")
    await create_property(save_fixture, name="Sold", is_archived=True)
    await create_transaction(
        save_fixture,
        campo,
        type=TransactionType.income,
        amount="50",
        date=dt.date(2026, 10, 1),
    )
    await create_transaction(
        save_fixture, campo, amount="20", date=dt.date(2026, 11, 2)
    )
    await create_transaction(
        save_fixture, colinas, amount="900", date=dt.date(2026, 11, 3)
    )
    await login(user)

    balances = (
        await client.get("/v1/balances/", params={"is_archived": "false"})
    ).json()

    assert [
        (
            b["property_name"],
            b["balance"],
            b["first_activity_date"],
            b["last_income_date"],
            b["last_activity_date"],
        )
        for b in balances
    ] == [
        ("Colinas 21", -900, "2026-11-03", None, "2026-11-03"),
        ("Campo 9", 30, "2026-10-01", "2026-10-01", "2026-11-02"),
    ]
