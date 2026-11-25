"""Copies the Laravel app's database into this one, as often as you like.

Until the switch-over the Laravel database is the truth: every run makes this
one match it. Properties are matched by name, users by email and
transactions by `(source, external_id)`, so a second run adds what is new, corrects what was
edited there and removes what was deleted there, and duplicates nothing.
The Laravel database is only read. Users are never deleted here: one that
exists only here is listed instead, as it may be someone added in this app.

Ends by comparing each property's balance, derived here, with the one the
Laravel triggers kept. A difference is a wrong rule or drift in the old table;
archived properties are shown but not counted, as that table stopped following
them.

Usage: python -m scripts.import_legacy <laravel-dsn> [--dry-run]
       e.g. postgresql:///bajalux-2026-08-04
"""

import asyncio
import datetime as dt
import json
import re
import sys
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

import asyncpg
from sqlalchemy import or_, select, true, update
from sqlalchemy.dialects.postgresql import insert

from baja.company.service import get_company
from baja.company.service import today as company_today
from baja.kit.db.models import RecordModel
from baja.kit.db.postgres import AsyncSession, create_async_sessionmaker
from baja.kit.utils import generate_uuid, utc_now
from baja.ledger.repository import TransactionRepository
from baja.ledger.service import affects_balance
from baja.models import (
    Checklist,
    ChecklistItem,
    ChecklistTemplateItem,
    ChecklistType,
    Company,
    Currency,
    GuestExpense,
    Invoice,
    InvoiceLine,
    PaymentMethod,
    Property,
    RecurringCharge,
    Role,
    Transaction,
    TransactionType,
    User,
)
from baja.postgres import create_async_engine
from baja.property.repository import PropertyRepository
from baja.recurring.repository import RecurringChargeRepository
from baja.user.repository import UserRepository

# Laravel's `houses.account_type`, as the rule its balance triggers applied.
BALANCE_METHODS = {
    "app": [PaymentMethod.cash],
    "bank": [PaymentMethod.debit_card, PaymentMethod.withdrawal],
}
PAYMENT_METHODS = {method.value: method for method in PaymentMethod} | {
    "visa": PaymentMethod.credit_card
}
# Laravel's Spatie roles. Only admins could manage users, which only owners do here.
ROLES = {"admin": Role.owner, "editor": Role.manager, "viewer": Role.homeowner}
# Rows Laravel never gave an id are keyed by their old primary key.
UNKEYED_SOURCE = "legacy"
# Every source the old system writes. Rows from these are the copy and follow
# the Laravel database, even sources the new app also writes, like the
# Shortcut's: until the switch-over its entries go to the old system.
LEGACY_SOURCES = {UNKEYED_SOURCE, "laravel", "reminders", "shortcut"}
BATCH = 1000

# What Laravel hard-coded, as it has no company table.
COMPANY = {
    "name": "Baja Luxury Management",
    "currency": Currency.MXN,
    "timezone": "America/Mazatlan",
    "usd_exchange_rate": Decimal("17.0"),
}


@dataclass(frozen=True)
class LegacyRecurringCharge:
    """One of Laravel's `add:recurring-*` commands, for one house."""

    house_id: int
    amount: Decimal
    payment_method: PaymentMethod
    category: str
    concept: str
    description: str
    day_of_month: int


def _charges(
    day: int,
    method: PaymentMethod,
    category: str,
    concept: str,
    description: str,
    amounts: dict[int, int],
) -> list[LegacyRecurringCharge]:
    return [
        LegacyRecurringCharge(
            house, Decimal(amount), method, category, concept, description, day
        )
        for house, amount in amounts.items()
    ]


CASH, CARD = PaymentMethod.cash, PaymentMethod.credit_card
LAST = 31
# Copied from app/Console/Commands/Recurring*.php, by house_id. Their comments
# name some houses wrongly (41 is Canadas 3): the import uses the real address.
RECURRING_CHARGES = [
    *_charges(
        10,
        CASH,
        "staff",
        "property management",
        "monthly property management fee",
        {
            1: 8500,
            2: 8500,
            3: 10000,
            4: 8500,
            5: 10000,
            6: 8500,
            7: 8500,
            8: 8500,
            9: 10000,
            10: 10000,
            11: 8500,
            12: 10000,
            13: 30000,
            14: 10000,
            16: 8500,
            17: 8500,
            18: 12000,
            19: 8500,
            20: 8500,
            21: 12000,
            23: 8000,
            24: 8500,
            25: 24000,
            26: 10000,
            28: 10000,
            29: 10000,
            30: 20000,
            31: 8500,
            32: 10000,
            33: 13000,
            34: 10000,
            35: 10000,
            36: 10000,
            38: 8000,
            39: 20000,
            41: 10000,
            42: 19000,
            43: 10000,
            44: 10000,
            45: 10000,
        },
    ),
    *_charges(
        15,
        CASH,
        "utilities",
        "landscaping",
        "monthly landscaping service",
        {
            2: 7000,
            13: 8000,
            16: 1800,
            20: 7000,
            25: 16000,
            32: 12000,
            39: 7000,
            44: 8000,
            45: 8000,
        },
    ),
    *_charges(15, CASH, "housekeeping", "housekeeping", "1/2 mari payment", {10: 7500}),
    *_charges(
        LAST, CASH, "housekeeping", "housekeeping", "2/2 mari payment", {10: 7500}
    ),
    *_charges(
        15, CASH, "housekeeping", "housekeeping", "1/2 gaby pay roll", {19: 17500}
    ),
    *_charges(
        LAST, CASH, "housekeeping", "housekeeping", "2/2 gaby pay roll", {19: 17500}
    ),
    *_charges(15, CASH, "staff", "staff", "1/2 payment enrique and karen", {33: 26800}),
    *_charges(
        LAST, CASH, "staff", "staff", "2/2 payment enrique and karen", {33: 26800}
    ),
    *_charges(15, CASH, "staff", "staff", "miguel monthly payment", {4: 1000, 9: 1000}),
    *_charges(15, CARD, "utilities", "starlink", "monthly fee", {13: 1305}),
    *_charges(15, CASH, "staff", "staff", "supervise house construction", {30: 16000}),
    *_charges(
        LAST, CASH, "utilities", "landscaping", "sandrita monthly payment", {30: 19500}
    ),
]


@dataclass(frozen=True)
class LegacyHouse:
    house_id: int
    address: str | None
    account_type: str
    is_active: bool


@dataclass(frozen=True)
class LegacyUser:
    user_id: int
    email: str | None
    name: str | None
    house_id: int | None
    roles: list[str]
    send_report: bool = False


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
    entered_by: int | None = None


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
    entered_by: int | None = None


@dataclass(frozen=True)
class LegacyTemplateItem:
    id: int
    type: str
    description: str
    position: int


@dataclass(frozen=True)
class LegacyChecklist:
    id: int
    house_id: int
    user_id: int
    type: str
    status: str
    completed_at: dt.datetime | None
    email_sent_to: list[str] | None
    created_at: dt.datetime | None


@dataclass(frozen=True)
class LegacyChecklistItem:
    id: int
    checklist_id: int
    description: str
    position: int
    is_checked: bool
    note: str | None
    checked_at: dt.datetime | None
    created_at: dt.datetime | None


@dataclass(frozen=True)
class LegacyInvoice:
    id: int
    house_id: int
    invoice_no: str
    recipient_name: str
    email: str
    invoice_date: dt.date
    total: Decimal
    created_at: dt.datetime | None


@dataclass(frozen=True)
class Legacy:
    houses: list[LegacyHouse]
    transactions: list[LegacyTransaction]
    balances: dict[int, Decimal]
    """By house: the table the Laravel triggers kept."""
    guest_expenses: list[LegacyGuestExpense] = field(default_factory=list)
    users: list[LegacyUser] = field(default_factory=list)
    recurring_charges: list[LegacyRecurringCharge] = field(default_factory=list)
    template_items: list[LegacyTemplateItem] = field(default_factory=list)
    checklists: list[LegacyChecklist] = field(default_factory=list)
    checklist_items: list[LegacyChecklistItem] = field(default_factory=list)
    invoices: list[LegacyInvoice] = field(default_factory=list)


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


@dataclass(frozen=True)
class ImportReport:
    balances: list[BalanceCheck]
    users_only_here: list[str]
    """Emails of users this database has and Laravel's doesn't."""


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
        users = await connection.fetch(
            "SELECT u.user_id, u.email, u.name, u.house_id, u.send_report, "
            "array_remove(array_agg(r.name ORDER BY r.name), NULL) AS roles "
            "FROM users u "
            "LEFT JOIN model_has_roles m "
            "ON m.model_id = u.user_id AND m.model_type = 'App\\Models\\User' "
            "LEFT JOIN roles r ON r.id = m.role_id "
            "GROUP BY u.user_id"
        )
        transactions = await _fetch(
            connection,
            "transactions",
            "id, house_id, type, amount, payment_method, category, concept, date, "
            "description, created_at",
        )
        guest_expenses = await _fetch(
            connection,
            "guest_expenses",
            "id, house_id, amount, category, concept, date, description, created_at",
        )
        balances = await connection.fetch("SELECT house_id, balance FROM balances")
        template_items = await connection.fetch(
            "SELECT id, type, description, position FROM checklist_template_items"
        )
        checklists = await connection.fetch(
            "SELECT id, house_id, user_id, type, status, completed_at, "
            "email_sent_to, created_at FROM checklists"
        )
        invoices = await connection.fetch(
            "SELECT id, house_id, invoice_no, recipient_name, email, invoice_date, "
            "total, created_at FROM invoices"
        )
        checklist_items = await connection.fetch(
            "SELECT id, checklist_id, description, position, is_checked, note, "
            "checked_at, created_at FROM checklist_items"
        )
    finally:
        await connection.close()
    return Legacy(
        houses=[LegacyHouse(**row) for row in houses],
        transactions=[LegacyTransaction(**row) for row in transactions],
        balances={row["house_id"]: row["balance"] for row in balances},
        guest_expenses=[LegacyGuestExpense(**row) for row in guest_expenses],
        users=[LegacyUser(**row) for row in users],
        recurring_charges=RECURRING_CHARGES,
        template_items=[LegacyTemplateItem(**row) for row in template_items],
        checklists=[
            LegacyChecklist(
                **{
                    **row,
                    # asyncpg hands json over as text.
                    "email_sent_to": json.loads(row["email_sent_to"])
                    if row["email_sent_to"]
                    else None,
                }
            )
            for row in checklists
        ],
        checklist_items=[LegacyChecklistItem(**row) for row in checklist_items],
        invoices=[LegacyInvoice(**row) for row in invoices],
    )


async def _fetch(
    connection: asyncpg.Connection, table: str, columns: str
) -> list[asyncpg.Record]:
    """Older Laravel databases predate `source`, `external_id` and `entered_by`."""
    later = await connection.fetch(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = $1 "
        "AND column_name IN ('source', 'external_id', 'entered_by')",
        table,
    )
    columns = ", ".join([columns, *sorted(row["column_name"] for row in later)])
    return list(await connection.fetch(f"SELECT {columns} FROM {table}"))


async def import_legacy(session: AsyncSession, legacy: Legacy) -> ImportReport:
    await _ensure_company(session)
    properties = await _import_houses(session, legacy.houses)
    users = await _import_users(session, legacy.users, properties)
    await _import_recurring_charges(session, legacy.recurring_charges, properties)
    transactions, transaction_problems = _rows(
        "transaction",
        legacy.transactions,
        lambda transaction: _transaction_row(transaction, properties, users),
    )
    guest_expenses, guest_expense_problems = _rows(
        "guest expense",
        legacy.guest_expenses,
        lambda guest_expense: _guest_expense_row(guest_expense, properties, users),
    )
    if problems := transaction_problems + guest_expense_problems:
        raise LegacyDataInvalid(problems)
    await _mirror(session, Transaction, transactions)
    await _mirror(session, GuestExpense, guest_expenses)
    await _import_checklists(session, legacy, properties, users)
    await _import_invoices(session, legacy.invoices, properties)
    balances = {
        balance.property_id: balance.balance
        for balance in await TransactionRepository.from_session(session).list_balances(
            true()
        )
    }
    imported = {user.id for user in users.values()}
    return ImportReport(
        balances=[
            BalanceCheck(
                property_name=property.name,
                old=legacy.balances.get(house_id, Decimal(0)),
                new=balances[property.id],
                is_archived=property.is_archived,
            )
            for house_id, property in sorted(
                properties.items(), key=lambda item: item[1].name.lower()
            )
        ],
        users_only_here=[
            user.email
            for user in await UserRepository.from_session(session).list_all()
            if user.id not in imported
        ],
    )


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


async def _ensure_company(session: AsyncSession) -> None:
    if (await session.execute(select(Company))).scalar_one_or_none() is None:
        session.add(Company(**COMPANY))
        await session.flush()


async def _import_recurring_charges(
    session: AsyncSession,
    charges: list[LegacyRecurringCharge],
    properties: dict[int, Property],
) -> None:
    """
    Laravel charges them until the switch-over, so each import moves them to
    start tomorrow: the last import before it hands them over.
    """
    if problems := [
        f"recurring charge {charge.concept!r}: unknown house {charge.house_id}"
        for charge in charges
        if charge.house_id not in properties
    ]:
        raise LegacyDataInvalid(problems)
    today = await company_today(session)
    repository = RecurringChargeRepository.from_session(session)
    existing = {
        (c.property_id, c.concept, c.description, c.day_of_month): c
        for c in await repository.list_all()
    }
    for legacy_charge in charges:
        property = properties[legacy_charge.house_id]
        values = {
            "amount": legacy_charge.amount,
            "payment_method": legacy_charge.payment_method,
            "category": legacy_charge.category,
            "charged_through": today,
        }
        key = (
            property.id,
            legacy_charge.concept,
            legacy_charge.description,
            legacy_charge.day_of_month,
        )
        if (charge := existing.get(key)) is not None:
            await repository.update(charge, values)
        else:
            await repository.create(
                RecurringCharge(
                    property=property,
                    concept=legacy_charge.concept,
                    description=legacy_charge.description,
                    day_of_month=legacy_charge.day_of_month,
                    **values,
                )
            )


async def _import_users(
    session: AsyncSession, users: list[LegacyUser], properties: dict[int, Property]
) -> dict[int, User]:
    problems = []
    emails: dict[str, int] = {}
    for legacy in users:
        email = (legacy.email or "").strip().lower()
        if not email:
            problems.append(f"user {legacy.user_id}: has no email")
        elif email in emails:
            problems.append(
                f"user {legacy.user_id}: same email as user {emails[email]}"
            )
        emails.setdefault(email, legacy.user_id)
        if len(legacy.roles) != 1 or legacy.roles[0] not in ROLES:
            problems.append(
                f"user {legacy.user_id}: roles {legacy.roles} are not one of "
                f"{', '.join(ROLES)}"
            )
        if legacy.house_id is not None and legacy.house_id not in properties:
            problems.append(f"user {legacy.user_id}: unknown house {legacy.house_id}")
    if problems:
        raise LegacyDataInvalid(problems)

    repository = UserRepository.from_session(session)
    imported: dict[int, User] = {}
    for legacy_user in users:
        email = (legacy_user.email or "").strip()
        role = ROLES[legacy_user.roles[0]]
        name = (legacy_user.name or "").strip() or None
        user = await repository.get_by_email(email)
        values = {"role": role, "receives_monthly_report": legacy_user.send_report}
        if user is None:
            user = await repository.create(User(email=email, name=name, **values))
        else:
            await repository.update(user, {**values, "name": name or user.name})
        # Owners and managers see every property: only homeowners are assigned.
        await repository.set_property_ids(
            user,
            {properties[legacy_user.house_id].id}
            if role == Role.homeowner and legacy_user.house_id is not None
            else set(),
        )
        imported[legacy_user.user_id] = user
    return imported


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
    transaction: LegacyTransaction,
    properties: dict[int, Property],
    users: dict[int, User],
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
    return _common_row(transaction, property, users) | {
        "type": type,
        "payment_method": payment_method,
        "affects_balance": affects_balance(property, type, payment_method),
    }


def _guest_expense_row(
    guest_expense: LegacyGuestExpense,
    properties: dict[int, Property],
    users: dict[int, User],
) -> dict[str, Any]:
    return _common_row(guest_expense, _property(guest_expense, properties), users)


def _property(
    item: LegacyTransaction | LegacyGuestExpense, properties: dict[int, Property]
) -> Property:
    if (property := properties.get(item.house_id)) is None:
        raise ValueError(f"unknown house {item.house_id}")
    return property


def _common_row(
    item: LegacyTransaction | LegacyGuestExpense,
    property: Property,
    users: dict[int, User],
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
        "entered_by_id": (
            users[item.entered_by].id if item.entered_by in users else None
        ),
        "deleted_at": None,
        "created_at": _utc(item.created_at),
    }


# Copied rows get ids derived from their Laravel ids: a second run finds them
# by id, and only they are version 5 (this app's own are version 7).
LEGACY_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL, "https://bajaluxurymgmt.com/laravel")


def legacy_id(kind: str, id: int) -> uuid.UUID:
    return uuid.uuid5(LEGACY_NAMESPACE, f"{kind}:{id}")


async def _import_checklists(
    session: AsyncSession,
    legacy: Legacy,
    properties: dict[int, Property],
    users: dict[int, User],
) -> None:
    types = {type.value for type in ChecklistType}
    checklist_ids = {checklist.id for checklist in legacy.checklists}
    problems = [
        f"checklist template item {item.id}: unknown type {item.type!r}"
        for item in legacy.template_items
        if item.type not in types
    ]
    for checklist in legacy.checklists:
        if checklist.type not in types:
            problems.append(
                f"checklist {checklist.id}: unknown type {checklist.type!r}"
            )
        if checklist.house_id not in properties:
            problems.append(
                f"checklist {checklist.id}: unknown house {checklist.house_id}"
            )
    problems += [
        f"checklist item {item.id}: unknown checklist {item.checklist_id}"
        for item in legacy.checklist_items
        if item.checklist_id not in checklist_ids
    ]
    if problems:
        raise LegacyDataInvalid(problems)

    await _mirror_by_id(
        session,
        ChecklistTemplateItem,
        [
            {
                "id": legacy_id("checklist_template_item", item.id),
                "type": ChecklistType(item.type),
                "description": item.description,
                "position": item.position,
                "deleted_at": None,
            }
            for item in legacy.template_items
        ],
    )
    await _mirror_by_id(
        session,
        Checklist,
        [
            {
                "id": legacy_id("checklist", checklist.id),
                "property_id": properties[checklist.house_id].id,
                "created_by_id": (
                    users[checklist.user_id].id if checklist.user_id in users else None
                ),
                "type": ChecklistType(checklist.type),
                "completed_at": (
                    _utc(checklist.completed_at or checklist.created_at)
                    if checklist.status == "completed"
                    else None
                ),
                "emailed_to": checklist.email_sent_to or [],
                "created_at": _utc(checklist.created_at),
                "deleted_at": None,
            }
            for checklist in legacy.checklists
        ],
    )
    await _mirror_by_id(
        session,
        ChecklistItem,
        [
            {
                "id": legacy_id("checklist_item", item.id),
                "checklist_id": legacy_id("checklist", item.checklist_id),
                "description": item.description,
                "position": item.position,
                "is_checked": item.is_checked,
                "note": item.note,
                "checked_at": _utc(item.checked_at) if item.checked_at else None,
                "created_at": _utc(item.created_at),
                "deleted_at": None,
            }
            for item in legacy.checklist_items
        ],
    )


INVOICE_NUMBER = re.compile(r"INV-(\d{4})-(\d+)")


async def _import_invoices(
    session: AsyncSession,
    invoices: list[LegacyInvoice],
    properties: dict[int, Property],
) -> None:
    """
    Laravel kept only an invoice's total, not its lines: each comes over as
    one line for that total, with no tax on top, so it still adds up to what
    was sent.
    """
    problems = []
    numbers = {}
    for invoice in invoices:
        if (match := INVOICE_NUMBER.fullmatch(invoice.invoice_no)) is None:
            problems.append(f"invoice {invoice.id}: number {invoice.invoice_no!r}")
        else:
            numbers[invoice.id] = (int(match[1]), int(match[2]))
        if invoice.house_id not in properties:
            problems.append(f"invoice {invoice.id}: unknown house {invoice.house_id}")
    if problems:
        raise LegacyDataInvalid(problems)

    rate = (await get_company(session)).usd_exchange_rate
    await _mirror_by_id(
        session,
        Invoice,
        [
            {
                "id": legacy_id("invoice", invoice.id),
                "property_id": properties[invoice.house_id].id,
                "year": numbers[invoice.id][0],
                "sequence": numbers[invoice.id][1],
                "recipient_name": invoice.recipient_name,
                "email": invoice.email,
                "issued_on": invoice.invoice_date,
                "due_on": invoice.invoice_date,
                "tax_rate": Decimal(0),
                "exchange_rate": rate,
                "subtotal": invoice.total,
                "tax": Decimal(0),
                "total": invoice.total,
                "sent_at": _utc(invoice.created_at),
                "created_at": _utc(invoice.created_at),
                "deleted_at": None,
            }
            for invoice in invoices
        ],
    )
    await _mirror_by_id(
        session,
        InvoiceLine,
        [
            {
                "id": legacy_id("invoice_line", invoice.id),
                "invoice_id": legacy_id("invoice", invoice.id),
                "position": 1,
                "description": f"As invoiced ({invoice.invoice_no})",
                "quantity": Decimal(1),
                "unit_price": invoice.total,
                "amount": invoice.total,
                "deleted_at": None,
            }
            for invoice in invoices
        ],
    )


async def _mirror_by_id(
    session: AsyncSession, model: type[RecordModel], rows: list[dict[str, Any]]
) -> None:
    """Makes the model's copied rows exactly `rows`, by their derived ids."""
    for batch in _batches(rows):
        statement = insert(model).values(batch)
        copied = [c for c in batch[0] if c not in {"id", "created_at"}]
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[model.id],
                set_={c: statement.excluded[c] for c in copied}
                | {"modified_at": utc_now()},
                where=or_(
                    *(
                        getattr(model, c).is_distinct_from(statement.excluded[c])
                        for c in copied
                    )
                ),
            )
        )
    keys = {row["id"] for row in rows}
    existing = await session.execute(select(model.id).where(model.deleted_at.is_(None)))
    gone = [id for (id,) in existing if id.version == 5 and id not in keys]
    for ids in _batches(gone):
        await session.execute(
            update(model).where(model.id.in_(ids)).values(deleted_at=utc_now())
        )
    for loaded in list(session.identity_map.values()):
        if isinstance(loaded, model):
            session.expire(loaded)


def _utc(moment: dt.datetime | None) -> dt.datetime:
    """Laravel kept UTC without saying so."""
    return moment.replace(tzinfo=dt.UTC) if moment else utc_now()


def _batches[T](items: list[T]) -> Iterable[list[T]]:
    for start in range(0, len(items), BATCH):
        yield items[start : start + BATCH]


async def main(dsn: str, *, dry_run: bool) -> int:
    legacy = await read_legacy(dsn)
    engine = create_async_engine("script")
    try:
        async with create_async_sessionmaker(engine)() as session:
            report = await import_legacy(session, legacy)
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
        f"{len(legacy.guest_expenses)} guest expenses, {len(legacy.users)} users, "
        f"{len(legacy.recurring_charges)} recurring charges, "
        f"{len(legacy.checklists)} checklists, {len(legacy.invoices)} invoices"
        + (" (dry run, nothing saved)" if dry_run else "")
    )
    checks = report.balances
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
    if report.users_only_here:
        print("Users only in this database, left as they are:")  # noqa: T201
        for email in report.users_only_here:
            print(f"  {email}")  # noqa: T201
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)  # noqa: T201
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1], dry_run="--dry-run" in sys.argv)))
