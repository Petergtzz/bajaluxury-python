import dataclasses
import datetime as dt
from decimal import Decimal

import pytest
from sqlalchemy import select

from baja.kit.db.postgres import AsyncSession
from baja.models import PaymentMethod, Property, Transaction
from scripts.import_legacy import (
    BalanceCheck,
    Legacy,
    LegacyDataInvalid,
    LegacyHouse,
    LegacyTransaction,
    import_legacy,
)
from tests.fixtures import SaveFixture, create_property, create_transaction

CAMPO = LegacyHouse(house_id=1, address=" Campo 9 ", account_type="app", is_active=True)
SOLEIL = LegacyHouse(house_id=40, address="Soleil", account_type="bank", is_active=True)
OLD = LegacyHouse(
    house_id=22, address="Soleil (old)", account_type="app", is_active=False
)


def transaction(id: int, house_id: int = 1, **changes: object) -> LegacyTransaction:
    values: dict[str, object] = {
        "id": id,
        "house_id": house_id,
        "type": "expense",
        "amount": Decimal("100.00"),
        "payment_method": "cash",
        "category": "utilities",
        "concept": "cfe",
        "date": dt.date(2026, 7, 1),
        "description": None,
        "created_at": dt.datetime(2026, 7, 1, 18, 30),
    }
    return LegacyTransaction(**(values | changes))  # type: ignore[arg-type]


LEGACY = Legacy(
    houses=[CAMPO, SOLEIL, OLD],
    transactions=[
        transaction(1, type="income", amount=Decimal("1000.00"), payment_method="WIRE"),
        transaction(2, amount=Decimal("250.50")),
        transaction(3, payment_method="credit card"),
        transaction(4, payment_method=""),
        transaction(5, 40, payment_method="debit card", amount=Decimal("70.00")),
        transaction(6, 40, payment_method="cash"),
        transaction(7, 22, source="reminders", external_id="R-7"),
    ],
    balances={1: Decimal("749.50"), 40: Decimal("-70.00"), 22: Decimal("55.00")},
)


async def transactions(session: AsyncSession) -> list[Transaction]:
    result = await session.execute(
        select(Transaction)
        .where(Transaction.deleted_at.is_(None))
        .order_by(Transaction.external_id)
    )
    return list(result.scalars())


async def test_copies_properties_with_their_balance_rule(
    session: AsyncSession,
) -> None:
    await import_legacy(session, LEGACY)

    properties = (
        await session.execute(select(Property).order_by(Property.name))
    ).scalars()
    assert [(p.name, p.is_archived, p.balance_methods) for p in properties] == [
        ("Campo 9", False, [PaymentMethod.cash]),
        ("Soleil", False, [PaymentMethod.debit_card, PaymentMethod.withdrawal]),
        ("Soleil (old)", True, [PaymentMethod.cash]),
    ]


async def test_copies_transactions_normalized(session: AsyncSession) -> None:
    await import_legacy(session, LEGACY)

    copied = {t.external_id: t for t in await transactions(session)}
    assert sorted(copied) == ["1", "2", "3", "4", "5", "6", "R-7"]
    assert (copied["1"].source, copied["1"].payment_method) == (
        "legacy",
        PaymentMethod.wire,
    )
    assert copied["4"].payment_method is None
    assert copied["R-7"].source == "reminders"
    assert copied["2"].amount == Decimal("250.50")
    assert copied["2"].created_at == dt.datetime(2026, 7, 1, 18, 30, tzinfo=dt.UTC)
    assert [copied[k].affects_balance for k in ("1", "2", "3", "4", "5", "6")] == [
        True,
        True,
        False,
        False,
        True,
        False,
    ]


async def test_compares_balances_with_the_old_table(session: AsyncSession) -> None:
    checks = await import_legacy(session, LEGACY)

    assert checks == [
        BalanceCheck("Campo 9", Decimal("749.50"), Decimal("749.50")),
        BalanceCheck("Soleil", Decimal("-70.00"), Decimal("-70.00")),
        BalanceCheck(
            "Soleil (old)", Decimal("55.00"), Decimal("-100.00"), is_archived=True
        ),
    ]


async def test_running_again_follows_the_old_database(session: AsyncSession) -> None:
    await import_legacy(session, LEGACY)
    edited = dataclasses.replace(LEGACY.transactions[1], amount=Decimal("300.00"))
    again = dataclasses.replace(
        LEGACY,
        transactions=[
            LEGACY.transactions[0],
            edited,
            *LEGACY.transactions[3:],
            transaction(8, concept="new since"),
        ],
    )

    await import_legacy(session, again)

    copied = {t.external_id: t for t in await transactions(session)}
    assert sorted(copied) == ["1", "2", "4", "5", "6", "8", "R-7"]
    assert copied["2"].amount == Decimal("300.00")


async def test_leaves_the_apps_own_entries_alone(
    session: AsyncSession, save_fixture: SaveFixture
) -> None:
    campo = await create_property(save_fixture, name="Campo 9")
    own_id = (await create_transaction(save_fixture, campo, source="web")).id

    await import_legacy(session, LEGACY)

    assert own_id in {t.id for t in await transactions(session)}


async def test_refuses_data_it_cannot_map_and_says_where(
    session: AsyncSession,
) -> None:
    broken = dataclasses.replace(
        LEGACY,
        transactions=[
            transaction(1, payment_method="bitcoin"),
            transaction(2, amount=Decimal(0)),
            transaction(3, house_id=99),
        ],
    )

    with pytest.raises(LegacyDataInvalid) as error:
        await import_legacy(session, broken)

    assert error.value.problems == [
        "transaction 1: unknown payment method 'bitcoin'",
        "transaction 2: amount 0 is not positive",
        "transaction 3: unknown house 99",
    ]
