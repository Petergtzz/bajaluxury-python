from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from baja.models import Role


class UserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str | None
    role: Role


class ManagedUserSchema(UserSchema):
    property_ids: list[UUID] = Field(
        description="The properties a homeowner sees. Empty for owners and managers."
    )


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str | None = Field(default=None, max_length=255)


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
