import datetime as dt
from uuid import UUID

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    Date,
    ForeignKey,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel

from .user import User


class MonthlyReport(RecordModel):
    """
    A homeowner's report for one month, claimed when it is queued.

    The claim is what makes sending safe to repeat: a month already claimed
    for someone is never queued for them again.
    """

    __tablename__ = "monthly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "month"),
        CheckConstraint("extract(day from month) = 1", name="month"),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=False
    )
    month: Mapped[dt.date] = mapped_column(Date, nullable=False)
    """Its first day."""
    sent_at: Mapped[dt.datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )

    user: Mapped[User] = relationship(User, lazy="raise")
