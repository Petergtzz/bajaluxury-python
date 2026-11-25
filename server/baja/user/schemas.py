from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from baja.models import Currency, Role


class PersonSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str | None
    role: Role


class UserSchema(PersonSchema):
    """Whoever is logged in, with what only they choose."""

    display_currency: Currency | None = Field(
        description="The currency they read amounts in; null for the company's."
    )


class ManagedUserSchema(PersonSchema):
    property_ids: list[UUID] = Field(
        description="The properties a homeowner sees. Empty for owners and managers."
    )


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=255)
    display_currency: Currency | None = Field(
        default=None,
        description="Only how amounts are shown, converted at the company's rate.",
    )


class ManagedUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr
    name: str | None = Field(default=None, max_length=255)
    role: Role
    property_ids: set[UUID] = Field(
        default_factory=set, description="Only for homeowners."
    )


class ManagedUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    email: EmailStr | None = None
    name: str | None = Field(default=None, max_length=255)
    role: Role | None = None
    property_ids: set[UUID] | None = Field(
        default=None, description="Replaces the assignments. Only for homeowners."
    )
