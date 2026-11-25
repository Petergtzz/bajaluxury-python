import datetime as dt
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from baja.kit.schemas import Money
from baja.models import Currency


class BucketSchema(BaseModel):
    key: str
    label: str


class BucketTotal(BaseModel):
    total: Money
    count: int = Field(description="How many expenses: the tracker's figure.")


class UtilitiesMonth(BaseModel):
    month: str = Field(description="`YYYY-MM`.")
    buckets: dict[str, BucketTotal]
    total: Money


class UtilitiesReport(BaseModel):
    """What went to each kind of bill, month by month."""

    property_id: UUID | None = Field(description="Null: every property visible.")
    property_name: str | None
    start: dt.date
    end: dt.date
    currency: Currency
    exchange_rate: Decimal | None
    buckets: list[BucketSchema]
    months: list[UtilitiesMonth] = Field(
        description="Every month the period touches, even an empty one."
    )
    totals: dict[str, BucketTotal]
    grand_total: Money
