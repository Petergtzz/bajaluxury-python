import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
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


class GuestExpense(RecordModel):
    """
    Spent on a renting guest's behalf, to be billed to them.

    Never part of the owner's ledger or balance.
    """

    __tablename__ = "guest_expenses"
    __table_args__ = (
        # Deleted rows keep their key: a retry after a delete must not bring it back.
        UniqueConstraint("source", "external_id"),
        CheckConstraint("amount > 0", name="amount"),
        Index("ix_guest_expenses_property_date", "property_id", "date"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    entered_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="set null"), nullable=True, default=None
    )
