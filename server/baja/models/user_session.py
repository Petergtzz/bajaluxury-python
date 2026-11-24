from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, TIMESTAMP, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel

from .user import User


class UserSession(RecordModel):
    """A browser that logged in. The cookie holds the token, this row its hash."""

    __tablename__ = "user_sessions"

    token: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
    user_agent: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=False, index=True
    )

    user: Mapped[User] = relationship(User, lazy="raise")
