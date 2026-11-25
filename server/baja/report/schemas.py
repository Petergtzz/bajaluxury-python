import datetime as dt
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from baja.models import RecipientKind, SendStatus

DEFAULT_SEND_DAY = 2


class ReportRecipientSchema(BaseModel):
    user_id: UUID
    email: str
    name: str | None
    kind: RecipientKind = Field(description="Addressed to them, or copied to them.")


class ReportSchema(BaseModel):
    """
    A property and the monthly statement it sends. Every active property has
    one, sending or not: no recipients is what "off" is.
    """

    property_id: UUID
    property_name: str
    send_day: int = Field(
        description="Day of the month it goes out, in the month after the one it covers."
    )
    recipients: list[ReportRecipientSchema]
    last_sent_at: dt.datetime | None


class RecipientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    kind: RecipientKind


class ReportUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    send_day: int = Field(default=DEFAULT_SEND_DAY, ge=1, le=28)
    recipients: list[RecipientUpdate] = Field(
        min_length=1,
        max_length=50,
        description=(
            "Replaces who receives it. Each must be able to see the property, and "
            "at least one is `to`. Turn a report off by deleting it."
        ),
    )


class ReportSendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: dt.date | None = Field(
        default=None,
        description="Any day of the month to send; the last whole month if left out.",
    )


class ReportSent(BaseModel):
    """What a send now set off."""

    month: dt.date = Field(description="First day of the month the email covers.")
    recipient_count: int = Field(description="How many people it was queued for.")


class SentStatementSchema(BaseModel):
    """One property's statement for one month, and what became of it."""

    id: UUID
    property_id: UUID
    property_name: str
    month: dt.date = Field(description="Its first day.")
    status: SendStatus
    sent_at: dt.datetime | None
    to: list[str]
    cc: list[str]
    error: str | None = Field(description="Why it didn't go, when it didn't.")
    has_statement: bool = Field(
        description="Whether the PDF it sent can be downloaded."
    )


class FailedStatementCount(BaseModel):
    count: int = Field(description="How many statements didn't go.")
