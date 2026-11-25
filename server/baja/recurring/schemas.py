import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from baja.kit.schemas import Amount, Money
from baja.models import PaymentMethod

DAY_OF_MONTH = "31, or any day a month lacks, means its last day."
DayOfMonth = Field(ge=1, le=31, description=DAY_OF_MONTH)


class RecurringChargeSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    amount: Money
    payment_method: PaymentMethod
    category: str
    concept: str
    description: str | None
    day_of_month: int
    next_charge_on: dt.date
    created_at: dt.datetime


class RecurringChargeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID
    amount: Amount
    payment_method: PaymentMethod
    category: str = Field(min_length=1, max_length=64)
    concept: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    day_of_month: int = DayOfMonth
    starts_on: dt.date | None = Field(
        default=None,
        description=(
            "The first day it may be charged. Today if left out: "
            "it never charges for days before it was set up."
        ),
    )


class RecurringChargeUpdate(BaseModel):
    """Changes apply from the next charge: months already charged stay as they were."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    amount: Amount | None = None
    payment_method: PaymentMethod | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    concept: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    day_of_month: int | None = Field(
        default=None, ge=1, le=31, description=DAY_OF_MONTH
    )
