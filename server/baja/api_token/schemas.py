import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TokenUserSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None


class ApiTokenSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str = Field(description="The device it is on, like Ana's iPhone.")
    user: TokenUserSchema = Field(description="Who it acts as.")
    last_used_at: dt.datetime | None
    created_at: dt.datetime


class ApiTokenCreated(ApiTokenSchema):
    token: str = Field(description="Shown only now: only its hash is kept.")


class ApiTokenCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=255)
