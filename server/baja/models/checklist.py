import datetime as dt
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check


class ChecklistType(StrEnum):
    check_in = "check_in"
    check_out = "check_out"
    weekly = "weekly"


class ChecklistTemplateItem(RecordModel):
    """One line of what a type of checklist asks, copied into each new one."""

    __tablename__ = "checklist_template_items"
    __table_args__ = (CheckConstraint(enum_check("type", ChecklistType), name="type"),)

    type: Mapped[ChecklistType] = mapped_column(
        StringEnum(ChecklistType, length=16), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)


class Checklist(RecordModel):
    """
    A walk through a property, item by item. Completing it sends its report
    and freezes it: what was reported is what stays.
    """

    __tablename__ = "checklists"
    __table_args__ = (
        CheckConstraint(enum_check("type", ChecklistType), name="type"),
        Index("ix_checklists_property_created", "property_id", "created_at"),
    )

    property_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="set null"), nullable=True
    )
    type: Mapped[ChecklistType] = mapped_column(
        StringEnum(ChecklistType, length=16), nullable=False
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    emailed_to: Mapped[list[str]] = mapped_column(
        ARRAY(String(320)), nullable=False, default=list, server_default=text("'{}'")
    )

    items: Mapped[list[ChecklistItem]] = relationship(
        "ChecklistItem",
        lazy="raise",
        order_by="ChecklistItem.position",
        primaryjoin="and_(ChecklistItem.checklist_id == Checklist.id, "
        "ChecklistItem.deleted_at.is_(None))",
        viewonly=True,
    )


class ChecklistItem(RecordModel):
    __tablename__ = "checklist_items"

    checklist_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("checklists.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_checked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    checked_at: Mapped[dt.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
