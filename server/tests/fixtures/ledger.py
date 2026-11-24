import datetime as dt
from decimal import Decimal

from baja.kit.utils import generate_uuid
from baja.ledger.service import affects_balance
from baja.models import (
    GuestExpense,
    PaymentMethod,
    Property,
    Transaction,
    TransactionType,
)
from tests.fixtures.database import SaveFixture


async def create_transaction(
    save_fixture: SaveFixture,
    property: Property,
    *,
    type: TransactionType = TransactionType.expense,
    amount: Decimal | str = "100.00",
    payment_method: PaymentMethod | None = PaymentMethod.cash,
    category: str = "utilities",
    concept: str = "cfe",
    date: dt.date = dt.date(2026, 11, 5),
    description: str | None = None,
    source: str = "web",
) -> Transaction:
    transaction = Transaction(
        property_id=property.id,
        type=type,
        amount=Decimal(amount),
        payment_method=payment_method,
        category=category,
        concept=concept,
        date=date,
        description=description,
        source=source,
        external_id=str(generate_uuid()),
        affects_balance=affects_balance(property, type, payment_method),
    )
    await save_fixture(transaction)
    return transaction


async def create_guest_expense(
    save_fixture: SaveFixture,
    property: Property,
    *,
    amount: Decimal | str = "456.50",
    category: str = "transport",
    concept: str = "airport pickup",
    date: dt.date = dt.date(2026, 11, 5),
    source: str = "web",
) -> GuestExpense:
    guest_expense = GuestExpense(
        property_id=property.id,
        amount=Decimal(amount),
        category=category,
        concept=concept,
        date=date,
        source=source,
        external_id=str(generate_uuid()),
    )
    await save_fixture(guest_expense)
    return guest_expense
