from decimal import Decimal
from zoneinfo import available_timezones

from pydantic import BaseModel, ConfigDict, Field, field_validator

from baja.models import Currency


class CompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    currency: Currency = Field(description="What every amount is in.")
    timezone: str = Field(description="Where the company's days start and end.")
    usd_exchange_rate: Decimal = Field(description="Its currency per US dollar.")


class CompanyUpdate(BaseModel):
    """The currency stays as it was set: every amount recorded is in it."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    timezone: str | None = Field(default=None, description="An IANA zone.")
    usd_exchange_rate: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=4,
        description="Its currency per US dollar, for statements in dollars and invoices.",
    )

    @field_validator("timezone")
    @classmethod
    def known_timezone(cls, value: str | None) -> str | None:
        if value is not None and value not in available_timezones():
            raise ValueError("That isn't a timezone, like America/Mazatlan.")
        return value
