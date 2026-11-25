from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from baja.models import Currency


class CompanySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    currency: Currency = Field(description="What every amount is in.")
    timezone: str = Field(description="Where the company's days start and end.")
    usd_exchange_rate: Decimal = Field(description="Its currency per US dollar.")
