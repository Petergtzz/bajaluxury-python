import datetime as dt
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check


class TransactionType(StrEnum):
    income = "income"
    expense = "expense"


class PaymentMethod(StrEnum):
    cash = "cash"
    credit_card = "credit card"
    debit_card = "debit card"
    withdrawal = "withdrawal"
    check = "check"
    wire = "wire"
    paypal = "paypal"


class Transaction(RecordModel):
    """One line of a property's ledger, in the company's currency."""

    __tablename__ = "transactions"
    __table_args__ = (
        # Deleted rows keep their key: a retry after a delete must not bring it back.
        UniqueConstraint("source", "external_id"),
        CheckConstraint(enum_check("type", TransactionType), name="type"),
        CheckConstraint(
            enum_check("payment_method", PaymentMethod), name="payment_method"
        ),
        CheckConstraint("amount > 0", name="amount"),
        Index("ix_transactions_property_date", "property_id", "date"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False
    )
    type: Mapped[TransactionType] = mapped_column(
        StringEnum(TransactionType, length=16), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        StringEnum(PaymentMethod, length=16), nullable=True
    )
    """Only missing on a few imported rows, where nobody recorded it."""
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    """Where the row came from (`web`, `shortcut`, `reminders`, ...)."""
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    """The row's identity within its source, so a resend records nothing twice."""
    affects_balance: Mapped[bool] = mapped_column(Boolean, nullable=False)
    """Decided when written, so changing a property's rule never rewrites history."""
    entered_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="set null"), nullable=True, default=None
    )
