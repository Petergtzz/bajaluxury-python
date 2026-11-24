import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Self

from pydantic import BaseModel, Field, field_validator, model_validator

from baja.models import PaymentMethod, TransactionType

INCOME_DEFAULTS: dict[str, Any] = {
    "category": "income",
    "concept": "deposit",
    "method": PaymentMethod.cash,
}


class ShortcutEntry(BaseModel):
    """
    What the Shortcut posts: picked from lists the API serves, so already tidy.

    Fields it leaves out arrive as empty strings, and text is kept lowercase,
    as the old intake did.
    """

    external_id: str = Field(
        min_length=1,
        max_length=200,
        description=(
            "Made once on the phone and resent on retry. An entry for several "
            "villas records `<id>-1`, `<id>-2`, ... one per villa."
        ),
    )
    amount: Decimal = Field(gt=0, max_digits=14)
    date: dt.date
    type: TransactionType = TransactionType.expense
    method: PaymentMethod | None = None
    concept: str = Field(default="", max_length=255)
    category: str = Field(default="", max_length=64)
    description: str = Field(default="", max_length=2000)
    is_guest: bool = False
    addresses: list[str] = Field(
        default_factory=list,
        description="Villa names. Each gets the full amount.",
    )

    @field_validator("addresses", mode="before")
    @classmethod
    def flatten_addresses(cls, value: Any) -> list[str]:
        """Shortcuts sends a list as a nested array or as one newline-separated item."""
        if isinstance(value, str):
            value = [value]
        names: list[str] = []
        for item in value or []:
            for part in item if isinstance(item, list | tuple) else [item]:
                names.extend(str(part).splitlines())
        return [name.strip() for name in names if name.strip()]

    @field_validator("concept", "category", "description", mode="before")
    @classmethod
    def tidy(cls, value: Any) -> Any:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("type", "method", mode="before")
    @classmethod
    def lowercase(cls, value: Any) -> Any:
        """The pickers show "Expense", "Credit Card"; nothing picked is ""."""
        if isinstance(value, str):
            return value.strip().lower() or None
        return value

    @field_validator("amount")
    @classmethod
    def to_cents(cls, value: Decimal) -> Decimal:
        cents = value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if cents <= 0:
            raise ValueError("must be at least 0.01")
        return cents

    @model_validator(mode="after")
    def apply_income_defaults(self) -> Self:
        """
        Income is always cash, deposit, income: the phone skips those sheets,
        so whatever arrives is overwritten rather than trusted.
        """
        if self.type == TransactionType.income and not self.is_guest:
            for field, value in INCOME_DEFAULTS.items():
                setattr(self, field, value)
            return self
        required = ["concept", "category"] + ([] if self.is_guest else ["method"])
        if missing := [field for field in required if not getattr(self, field)]:
            raise ValueError(f"An expense needs {', '.join(missing)}.")
        return self


class Villas(BaseModel):
    """Wrapped: Shortcuts hands a bare array to Choose from List as one item."""

    villas: list[str]


class Categories(BaseModel):
    categories: list[str]


class ShortcutConfirmation(BaseModel):
    """The phone's notification after saving."""

    inserted: int
    title: str
    summary: str
