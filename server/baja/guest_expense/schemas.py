import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from baja.kit.schemas import Amount, Money


class GuestExpenseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    amount: Money
    category: str
    concept: str
    date: dt.date
    description: str | None
    source: str
    external_id: str
    entered_by_id: UUID | None
    created_at: dt.datetime


class GuestExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID
    amount: Amount
    category: str = Field(min_length=1, max_length=64)
    concept: str = Field(min_length=1, max_length=255)
    date: dt.date
    description: str | None = Field(default=None, max_length=2000)
    external_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description=(
            "Your id for this entry. Send the same one on a retry: "
            "it returns the guest expense already recorded instead of a second one."
        ),
    )


class GuestExpenseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID | None = None
    amount: Amount | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    concept: str | None = Field(default=None, min_length=1, max_length=255)
    date: dt.date | None = None
    description: str | None = Field(default=None, max_length=2000)
