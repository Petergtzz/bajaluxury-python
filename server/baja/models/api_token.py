from datetime import datetime
from uuid import UUID

from sqlalchemy import CHAR, TIMESTAMP, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel

from .user import User


class ApiToken(RecordModel):
    """
    A device calling the API as a user, such as a phone running the Shortcut.

    One per device, so a lost one is revoked (deleted) without touching the
    others. The device holds the token, this row its hash.
    """

    __tablename__ = "api_tokens"

    token: Mapped[str] = mapped_column(CHAR(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None
    )
    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=False, index=True
    )

    user: Mapped[User] = relationship(User, lazy="raise")
