import datetime as dt
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from baja.kit.schemas import Money

Quantity = Annotated[Decimal, Field(gt=0, max_digits=10, decimal_places=2)]
Price = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]


class InvoiceLineSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    description: str
    quantity: Money
    unit_price: Money
    amount: Money
    guest_expense_id: UUID | None


class InvoiceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: str
    property_id: UUID
    recipient_name: str
    email: str
    issued_on: dt.date
    due_on: dt.date
    tax_rate: Decimal
    exchange_rate: Decimal = Field(description="Company currency per US dollar.")
    subtotal: Money
    tax: Money
    total: Money
    payment_details: str | None
    notes: str | None
    created_by_id: UUID | None
    sent_at: dt.datetime | None
    created_at: dt.datetime
    lines: list[InvoiceLineSchema]


class InvoiceLineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Field(min_length=1, max_length=255)
    quantity: Quantity = Decimal(1)
    unit_price: Price
    guest_expense_id: UUID | None = Field(
        default=None, description="The guest expense this line bills."
    )


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    property_id: UUID
    recipient_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    issued_on: dt.date
    due_on: dt.date
    tax_rate: Decimal = Field(
        default=Decimal("0.16"),
        ge=0,
        le=1,
        max_digits=5,
        decimal_places=4,
        description="As a fraction: 0.16 is 16% VAT.",
    )
    exchange_rate: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=4,
        description="Company currency per US dollar. The company's if left out.",
    )
    payment_details: str | None = Field(default=None, max_length=2000)
    notes: str | None = Field(default=None, max_length=2000)
    lines: list[InvoiceLineCreate] = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def due_after_issue(self) -> Self:
        if self.due_on < self.issued_on:
            raise ValueError("It can't be due before it is issued.")
        return self
