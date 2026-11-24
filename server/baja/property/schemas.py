from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from baja.models import PaymentMethod

BalanceMethods = Annotated[
    list[PaymentMethod],
    AfterValidator(lambda methods: list(dict.fromkeys(methods))),
    Field(
        description=(
            "The payment methods whose expenses come out of the owner's balance "
            "with us. Changing them applies to transactions recorded from then on."
        )
    ),
]


class PropertySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None
    is_archived: bool
    balance_methods: list[PaymentMethod]
    created_at: datetime


class PropertyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255, description="Unique.")
    address: str | None = Field(default=None, max_length=500)
    balance_methods: BalanceMethods = [PaymentMethod.cash]


class PropertyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    is_archived: bool | None = None
    balance_methods: BalanceMethods | None = None
