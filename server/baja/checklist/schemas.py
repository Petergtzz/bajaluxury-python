import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from baja.models import ChecklistType

Description = Field(min_length=1, max_length=2000)


class TemplateItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: ChecklistType
    description: str
    position: int


class TemplateItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    type: ChecklistType
    description: str = Description


class TemplateItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    description: str = Description


class TemplateOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: ChecklistType
    item_ids: list[UUID] = Field(
        description="Every item of the type, in the order wanted: no more, no fewer."
    )


class ChecklistItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    description: str
    position: int
    is_checked: bool
    note: str | None
    checked_at: dt.datetime | None


class ChecklistSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    property_id: UUID
    type: ChecklistType
    created_by_id: UUID | None
    created_at: dt.datetime
    completed_at: dt.datetime | None
    emailed_to: list[str]
    items: list[ChecklistItemSchema]


class ChecklistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: UUID
    type: ChecklistType


class ChecklistItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_checked: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


class ChecklistComplete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipients: list[EmailStr] = Field(
        min_length=1, description="Who is emailed its report."
    )
