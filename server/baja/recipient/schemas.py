from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from baja.models import RecipientKind


class RecipientSchema(BaseModel):
    user_id: UUID
    email: str
    name: str | None
    kind: RecipientKind = Field(description="Addressed to them, or copied to them.")


class RecipientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    kind: RecipientKind
