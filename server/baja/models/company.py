from decimal import Decimal
from enum import StrEnum

from sqlalchemy import CheckConstraint, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check


class Currency(StrEnum):
    MXN = "MXN"
    USD = "USD"


class Company(RecordModel):
    """The business itself: its name, money and clock. Exactly one row."""

    __tablename__ = "companies"
    __table_args__ = (
        Index("ix_companies_singleton", text("(true)"), unique=True),
        CheckConstraint(enum_check("currency", Currency), name="currency"),
        CheckConstraint("usd_exchange_rate > 0", name="usd_exchange_rate"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[Currency] = mapped_column(
        StringEnum(Currency, length=3), nullable=False
    )
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    usd_exchange_rate: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    """How many units of `currency` one US dollar is shown at."""
