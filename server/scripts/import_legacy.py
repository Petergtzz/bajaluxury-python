"""Copies the Laravel app's database into this one, as often as you like.

Until the switch-over the Laravel database is the truth: every run makes this
one match it. Properties are matched by name and transactions by
`(source, external_id)`, so a second run adds what is new, corrects what was
edited there and removes what was deleted there, and duplicates nothing.
The Laravel database is only read.

Ends by comparing each property's balance, derived here, with the one the
Laravel triggers kept. A difference is a wrong rule or drift in the old table;
archived properties are shown but not counted, as that table stopped following
them.

Usage: python -m scripts.import_legacy <laravel-dsn> [--dry-run]
       e.g. postgresql:///bajalux-2026-08-04
"""

import asyncio
import datetime as dt
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import asyncpg
from sqlalchemy import or_, select, true, update
from sqlalchemy.dialects.postgresql import insert

from baja.kit.db.postgres import AsyncSession, create_async_sessionmaker
from baja.kit.utils import generate_uuid, utc_now
from baja.ledger.repository import TransactionRepository
from baja.ledger.service import affects_balance
from baja.models import (
    GuestExpense,
    PaymentMethod,
    Property,
    Transaction,
    TransactionType,
)
from baja.postgres import create_async_engine
from baja.property.repository import PropertyRepository

# Laravel's `houses.account_type`, as the rule its balance triggers applied.
BALANCE_METHODS = {
    "app": [PaymentMethod.cash],
    "bank": [PaymentMethod.debit_card, PaymentMethod.withdrawal],
}
PAYMENT_METHODS = {method.value: method for method in PaymentMethod} | {
    "visa": PaymentMethod.credit_card
}
# Rows Laravel never gave an id are keyed by their old primary key.
UNKEYED_SOURCE = "legacy"
# Every source the old system writes. Rows from these are the copy and follow
# the Laravel database, even sources the new app also writes, like the
# Shortcut's: until the switch-over its entries go to the old system.
LEGACY_SOURCES = {UNKEYED_SOURCE, "laravel", "reminders", "shortcut"}
BATCH = 1000


@dataclass(frozen=True)
class LegacyHouse:
    house_id: int
    address: str | None
    account_type: str
    is_active: bool


@dataclass(frozen=True)
class LegacyTransaction:
    id: int
    house_id: int
    type: str
    amount: Decimal
    payment_method: str
    category: str | None
    concept: str
    date: dt.date
    description: str | None
    created_at: dt.datetime | None
    source: str | None = None
    external_id: str | None = None


@dataclass(frozen=True)
class LegacyGuestExpense:
    id: int
    house_id: int
    amount: Decimal
    category: str | None
    concept: str
    date: dt.date
    description: str | None
    created_at: dt.datetime | None
    source: str | None = None
    external_id: str | None = None


@dataclass(frozen=True)
class Legacy:
    houses: list[LegacyHouse]
    transactions: list[LegacyTransaction]
    balances: dict[int, Decimal]
    """By house: the table the Laravel triggers kept."""
    guest_expenses: list[LegacyGuestExpense] = field(default_factory=list)


@dataclass(frozen=True)
class BalanceCheck:
    property_name: str
    old: Decimal
    new: Decimal
    is_archived: bool = False
    """The old table stopped following these, so a difference is expected."""

    @property
    def matches(self) -> bool:
        return self.old == self.new


class LegacyDataInvalid(Exception):
    def __init__(self, problems: list[str]) -> None:
        super().__init__("\n".join(problems))
        self.problems = problems


async def read_legacy(dsn: str) -> Legacy:
    connection = await asyncpg.connect(dsn)
    try:
        houses = await connection.fetch(
            "SELECT house_id, address, account_type, is_active FROM houses"
        )
        transactions = await _fetch_keyed(
            connection,
            "transactions",
            "id, house_id, type, amount, payment_method, category, concept, date, "
            "description, created_at",
        )
        guest_expenses = await _fetch_keyed(
            connection,
            "guest_expenses",
            "id, house_id, amount, category, concept, date, description, created_at",
        )
        balances = await connection.fetch("SELECT house_id, balance FROM balances")
    finally:
        await connection.close()
    return Legacy(
        houses=[LegacyHouse(**row) for row in houses],
        transactions=[LegacyTransaction(**row) for row in transactions],
        balances={row["house_id"]: row["balance"] for row in balances},
        guest_expenses=[LegacyGuestExpense(**row) for row in guest_expenses],
    )


async def _fetch_keyed(
    connection: asyncpg.Connection, table: str, columns: str
) -> list[asyncpg.Record]:
    """Older Laravel databases predate `source` and `external_id`."""
    keyed = await connection.fetchval(
        "SELECT count(*) = 2 FROM information_schema.columns "
        "WHERE table_name = $1 AND column_name IN ('source', 'external_id')",
        table,
    )
    if keyed:
        columns += ", source, external_id"
    return list(await connection.fetch(f"SELECT {columns} FROM {table}"))


async def import_legacy(session: AsyncSession, legacy: Legacy) -> list[BalanceCheck]:
    properties = await _import_houses(session, legacy.houses)
    transactions, transaction_problems = _rows(
        "transaction",
        legacy.transactions,
        lambda transaction: _transaction_row(transaction, properties),
    )
    guest_expenses, guest_expense_problems = _rows(
        "guest expense",
        legacy.guest_expenses,
        lambda guest_expense: _guest_expense_row(guest_expense, properties),
    )
    if problems := transaction_problems + guest_expense_problems:
        raise LegacyDataInvalid(problems)
    await _mirror(session, Transaction, transactions)
    await _mirror(session, GuestExpense, guest_expenses)
    balances = {
        balance.property_id: balance.balance
        for balance in await TransactionRepository.from_session(session).list_balances(
            true()
        )
    }
    return [
        BalanceCheck(
            property_name=property.name,
            old=legacy.balances.get(house_id, Decimal(0)),
            new=balances[property.id],
            is_archived=property.is_archived,
        )
        for house_id, property in sorted(
            properties.items(), key=lambda item: item[1].name.lower()
        )
    ]


async def _import_houses(
    session: AsyncSession, houses: list[LegacyHouse]
) -> dict[int, Property]:
    problems = []
    for house in houses:
        if not (house.address or "").strip():
            problems.append(f"house {house.house_id}: has no address")
        if house.account_type not in BALANCE_METHODS:
            problems.append(
                f"house {house.house_id}: unknown account type {house.account_type!r}"
            )
    if problems:
        raise LegacyDataInvalid(problems)

    repository = PropertyRepository.from_session(session)
    properties: dict[int, Property] = {}
    for house in houses:
        name = (house.address or "").strip()
        values = {
            "is_archived": not house.is_active,
            "balance_methods": BALANCE_METHODS[house.account_type],
        }
        property = await repository.get_by_name(name)
        if property is None:
            property = await repository.create(Property(name=name, **values))
        else:
            await repository.update(property, values)
        properties[house.house_id] = property
    return properties


def _rows[L: LegacyTransaction | LegacyGuestExpense](
    kind: str, items: list[L], to_row: Callable[[L], dict[str, Any]]
) -> tuple[list[dict[str, Any]], list[str]]:
    rows, problems = [], []
    for item in items:
        try:
            rows.append(to_row(item))
        except ValueError as e:
            problems.append(f"{kind} {item.id}: {e}")
    return rows, problems


async def _mirror(
    session: AsyncSession,
    model: type[Transaction | GuestExpense],
    rows: list[dict[str, Any]],
) -> None:
    """Makes the model's imported rows exactly `rows`, keyed by source and id."""
    for batch in _batches(rows):
        statement = insert(model).values(batch)
        copied = [
            column
            for column in batch[0]
            if column not in {"id", "source", "external_id", "created_at"}
        ]
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[model.source, model.external_id],
                set_={column: statement.excluded[column] for column in copied}
                | {"modified_at": utc_now()},
                where=or_(
                    *(
                        getattr(model, column).is_distinct_from(
                            statement.excluded[column]
                        )
                        for column in copied
                    )
                ),
            )
        )

    keys = {(row["source"], row["external_id"]) for row in rows}
    imported = await session.execute(
        select(model.id, model.source, model.external_id).where(
            model.source.in_(LEGACY_SOURCES | {source for source, _ in keys}),
            model.deleted_at.is_(None),
        )
    )
    gone = [
        id for id, source, external_id in imported if (source, external_id) not in keys
    ]
    for ids in _batches(gone):
        await session.execute(
            update(model).where(model.id.in_(ids)).values(deleted_at=utc_now())
        )
    # The bulk writes bypassed any of these rows already loaded in the session.
    for loaded in list(session.identity_map.values()):
        if isinstance(loaded, model):
            session.expire(loaded)


def _transaction_row(
    transaction: LegacyTransaction, properties: dict[int, Property]
) -> dict[str, Any]:
    property = _property(transaction, properties)
    try:
        type = TransactionType(transaction.type)
    except ValueError:
        raise ValueError(f"unknown type {transaction.type!r}") from None
    method = transaction.payment_method.strip().lower()
    if method and method not in PAYMENT_METHODS:
        raise ValueError(f"unknown payment method {transaction.payment_method!r}")
    payment_method = PAYMENT_METHODS[method] if method else None
    return _common_row(transaction, property) | {
        "type": type,
        "payment_method": payment_method,
        "affects_balance": affects_balance(property, type, payment_method),
    }


def _guest_expense_row(
    guest_expense: LegacyGuestExpense, properties: dict[int, Property]
) -> dict[str, Any]:
    return _common_row(guest_expense, _property(guest_expense, properties))


def _property(
    item: LegacyTransaction | LegacyGuestExpense, properties: dict[int, Property]
) -> Property:
    if (property := properties.get(item.house_id)) is None:
        raise ValueError(f"unknown house {item.house_id}")
    return property


def _common_row(
    item: LegacyTransaction | LegacyGuestExpense, property: Property
) -> dict[str, Any]:
    if item.amount <= 0:
        raise ValueError(f"amount {item.amount} is not positive")
    if not item.category:
        raise ValueError("has no category")
    if item.external_id:
        source, external_id = item.source or UNKEYED_SOURCE, item.external_id
    else:
        source, external_id = UNKEYED_SOURCE, str(item.id)
    return {
        "id": generate_uuid(),
        "property_id": property.id,
        "amount": item.amount,
        "category": item.category,
        "concept": item.concept,
        "date": item.date,
        "description": item.description,
        "source": source,
        "external_id": external_id,
        "deleted_at": None,
        # Laravel kept UTC without saying so.
        "created_at": (
            item.created_at.replace(tzinfo=dt.UTC) if item.created_at else utc_now()
        ),
    }


def _batches[T](items: list[T]) -> Iterable[list[T]]:
    for start in range(0, len(items), BATCH):
        yield items[start : start + BATCH]


async def main(dsn: str, *, dry_run: bool) -> int:
    legacy = await read_legacy(dsn)
    engine = create_async_engine("script")
    try:
        async with create_async_sessionmaker(engine)() as session:
            checks = await import_legacy(session, legacy)
            if dry_run:
                await session.rollback()
            else:
                await session.commit()
    except LegacyDataInvalid as e:
        print("Nothing imported. Fix these in the Laravel database first:")  # noqa: T201
        print(e)  # noqa: T201
        return 1
    finally:
        await engine.dispose()

    print(  # noqa: T201
        f"{len(legacy.houses)} properties, {len(legacy.transactions)} transactions, "
        f"{len(legacy.guest_expenses)} guest expenses"
        + (" (dry run, nothing saved)" if dry_run else "")
    )
    width = max(len(check.property_name) for check in checks)
    for check in checks:
        print(  # noqa: T201
            f"{check.property_name:<{width}}  old {check.old:>14,.2f}  "
            f"new {check.new:>14,.2f}  "
            + ("OK" if check.matches else f"DIFFERENT by {check.new - check.old:,.2f}")
            + (" (archived)" if check.is_archived else "")
        )
    different = sum(not check.matches and not check.is_archived for check in checks)
    print(f"{different} balance(s) of active properties differ")  # noqa: T201
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], dry_run="--dry-run" in sys.argv)))
