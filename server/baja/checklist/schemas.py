import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from baja.models import ChecklistType
from baja.recipient.schemas import RecipientSchema, RecipientUpdate

Description = Field(min_length=1, max_length=2000)


class TemplateItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: ChecklistType
    description: str
    position: int


class TemplateItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: UUID | None = Field(
        default=None, description="An item already on the list; none for a new one."
    )
    description: str = Description


class TemplateUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[TemplateItemWrite] = Field(
        max_length=200, description="The whole list, in the order it is walked."
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
    emailed_cc: list[str]
    items: list[ChecklistItemSchema]


class ChecklistCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    property_id: UUID
    type: ChecklistType


class ChecklistItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    is_checked: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


class ChecklistPropertySchema(BaseModel):
    """A property, and who hears about the checklists completed there."""

    property_id: UUID
    property_name: str
    recipients: list[RecipientSchema]


class ChecklistRecipientsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipients: list[RecipientUpdate] = Field(
        max_length=50,
        description=(
            "Replaces who hears about it. Each must be able to see the property, and "
            "at least one is `to`. Empty is nobody: the company's owners still do."
        ),
    )
