import datetime as dt
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer

from baja.models import PaymentMethod, TransactionType

# A JSON number for clients; Decimal inside, so sums stay exact to the cent.
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Amount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class TransactionSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    type: TransactionType
    amount: Money
    payment_method: PaymentMethod | None
    category: str
    concept: str
    date: dt.date
    description: str | None
    source: str
    external_id: str
    affects_balance: bool = Field(
        description="Whether it moved the owner's balance with us."
    )
    entered_by_id: UUID | None
    created_at: dt.datetime


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID
    type: TransactionType
    amount: Amount
    payment_method: PaymentMethod
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
            "it returns the transaction already recorded instead of a second one."
        ),
    )


class TransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID | None = None
    type: TransactionType | None = None
    amount: Amount | None = None
    payment_method: PaymentMethod | None = None
    category: str | None = Field(default=None, min_length=1, max_length=64)
    concept: str | None = Field(default=None, min_length=1, max_length=255)
    date: dt.date | None = None
    description: str | None = Field(default=None, max_length=2000)


class PropertyBalance(BaseModel):
    property_id: UUID
    property_name: str
    balance: Money = Field(
        description="What the owner has with us: negative when they owe us."
    )
    last_income_date: dt.date | None
    last_activity_date: dt.date | None
