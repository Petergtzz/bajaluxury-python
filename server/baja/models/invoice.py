import datetime as dt
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    select,
)
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from baja.kit.db.models import RecordModel

from .guest_expense import GuestExpense


class Invoice(RecordModel):
    """
    A bill to a renting guest, usually for their guest expenses.

    Kept whole, lines and rates included, so it can be shown and printed
    again as it was sent.
    """

    __tablename__ = "invoices"
    __table_args__ = (
        # Deleted ones keep their number: a number is never given out twice.
        UniqueConstraint("year", "sequence"),
        CheckConstraint("tax_rate >= 0", name="tax_rate"),
        CheckConstraint("exchange_rate > 0", name="exchange_rate"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    issued_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    due_on: Mapped[dt.date] = mapped_column(Date, nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    """Company currency per US dollar, for the dollar column."""
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    sent_at: Mapped[dt.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )

    lines: Mapped[list[InvoiceLine]] = relationship(
        "InvoiceLine",
        lazy="raise",
        order_by="InvoiceLine.position",
        primaryjoin="and_(InvoiceLine.invoice_id == Invoice.id, "
        "InvoiceLine.deleted_at.is_(None))",
        viewonly=True,
    )

    @property
    def number(self) -> str:
        return f"INV-{self.year}-{self.sequence:03d}"


class InvoiceLine(RecordModel):
    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="quantity"),
        CheckConstraint("unit_price >= 0", name="unit_price"),
    )

    invoice_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("invoices.id", ondelete="cascade"), nullable=False, index=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    guest_expense_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("guest_expenses.id"), nullable=True, index=True
    )
    """The guest expense it bills, if it bills one."""


def _billed_by() -> Any:
    return (
        select(InvoiceLine.invoice_id)
        .join(Invoice, Invoice.id == InvoiceLine.invoice_id)
        .where(
            InvoiceLine.guest_expense_id == GuestExpense.id,
            InvoiceLine.deleted_at.is_(None),
            Invoice.deleted_at.is_(None),
        )
        .limit(1)
        .scalar_subquery()
    )


# Read from the invoice lines, not stored twice: deleting an invoice frees
# its guest expenses with nothing else to keep in step.
GuestExpense.invoice_id = column_property(_billed_by())
