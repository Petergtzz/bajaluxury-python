import builtins
import datetime as dt
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    SmallInteger,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check
from baja.recurring.dates import next_due

from .property import Property
from .transaction import PaymentMethod


class RecurringCharge(RecordModel):
    """An expense charged to a property every month, such as its management fee."""

    __tablename__ = "recurring_charges"
    __table_args__ = (
        CheckConstraint(
            enum_check("payment_method", PaymentMethod), name="payment_method"
        ),
        CheckConstraint("amount > 0", name="amount"),
        CheckConstraint("day_of_month BETWEEN 1 AND 31", name="day_of_month"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    payment_method: Mapped[PaymentMethod] = mapped_column(
        StringEnum(PaymentMethod, length=16), nullable=False
    )
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    concept: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    day_of_month: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    """Past the month's end it falls on its last day: 31 is always the last day."""
    charged_through: Mapped[dt.date] = mapped_column(Date, nullable=False)
    """
    The job charges what falls due after this day, then moves it to today.

    Only ever forward: a month it has passed is never charged again, whatever
    changes in the meantime.
    """

    property: Mapped[Property] = relationship(Property, lazy="raise")

    @builtins.property  # `property` here is the relationship
    def next_charge_on(self) -> dt.date:
        return next_due(self.day_of_month, self.charged_through)
