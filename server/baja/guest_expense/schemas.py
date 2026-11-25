import datetime as dt
from dataclasses import dataclass
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
    invoice_id: UUID | None = Field(
        description="The invoice that bills it, if one does."
    )
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


@dataclass(frozen=True)
class GuestExpenseFilters:
    """What narrows a list of guest expenses; nothing set lists them all."""

    property_id: UUID | None = None
    category: str | None = None
    start_date: dt.date | None = None
    end_date: dt.date | None = None
    invoiced: bool | None = None


class GuestExpenseSummary(BaseModel):
    """What the listed guest expenses add up to, across every page."""

    count: int
    total: Money
    billed_total: Money = Field(description="The part an invoice already bills.")
