import datetime as dt
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    LargeBinary,
    SmallInteger,
    String,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import (
    Mapped,
    column_property,
    deferred,
    mapped_column,
    relationship,
)

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check

from .property import Property
from .user import User


class RecipientKind(StrEnum):
    to = "to"
    cc = "cc"


class SendStatus(StrEnum):
    queued = "queued"
    sent = "sent"
    failed = "failed"


class PropertyReport(RecordModel):
    """
    A property's monthly statement, and when it goes out. It exists while
    someone receives it: turning it off is deleting it.
    """

    __tablename__ = "property_reports"
    __table_args__ = (
        Index(
            "ix_property_reports_property",
            "property_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint("send_day BETWEEN 1 AND 28", name="send_day"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id", ondelete="cascade"), nullable=False
    )
    send_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    """In the month after the one it covers; never past the 28th, which every month has."""

    property: Mapped[Property] = relationship(Property, lazy="raise")
    recipients: Mapped[list[PropertyReportRecipient]] = relationship(
        "PropertyReportRecipient",
        lazy="raise",
        primaryjoin="and_(PropertyReportRecipient.property_report_id == PropertyReport.id, "
        "PropertyReportRecipient.deleted_at.is_(None))",
        viewonly=True,
    )


class PropertyReportRecipient(RecordModel):
    __tablename__ = "property_report_recipients"
    __table_args__ = (
        Index(
            "ix_property_report_recipients_report_user",
            "property_report_id",
            "user_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(enum_check("kind", RecipientKind), name="kind"),
    )

    property_report_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("property_reports.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=False, index=True
    )
    kind: Mapped[RecipientKind] = mapped_column(
        StringEnum(RecipientKind, length=2), nullable=False
    )

    user: Mapped[User] = relationship(User, lazy="raise")


class ReportSend(RecordModel):
    """
    One property's statement for one month, and what became of it. Sending a
    month again sends it anew in the same record: one per property and month.
    """

    __tablename__ = "report_sends"
    __table_args__ = (
        Index(
            "ix_report_sends_property_month",
            "property_id",
            "month",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(enum_check("status", SendStatus), name="status"),
        CheckConstraint("extract(day from month) = 1", name="month"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("properties.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    month: Mapped[dt.date] = mapped_column(Date, nullable=False)
    """Its first day."""
    status: Mapped[SendStatus] = mapped_column(
        StringEnum(SendStatus, length=8), nullable=False
    )
    to_addresses: Mapped[list[str]] = mapped_column(ARRAY(String(320)), nullable=False)
    cc_addresses: Mapped[list[str]] = mapped_column(ARRAY(String(320)), nullable=False)
    sent_at: Mapped[dt.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    error: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    statement: Mapped[bytes | None] = deferred(
        mapped_column(LargeBinary, nullable=True, default=None)
    )
    """The PDF exactly as it went, kept for the history: a statement made later
    from the ledger could differ from what the owner received."""

    property: Mapped[Property] = relationship(Property, lazy="raise")


# Whether a PDF is kept, asked of the database without loading the file.
ReportSend.has_statement = column_property(
    ReportSend.__table__.c.statement.is_not(None)
)
