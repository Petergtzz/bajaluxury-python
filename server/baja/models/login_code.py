from datetime import datetime

from sqlalchemy import CHAR, TIMESTAMP, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel


class LoginCode(RecordModel):
    """A one-time code emailed to someone logging in. Only its hash is kept."""

    __tablename__ = "login_codes"
    __table_args__ = (Index("ix_login_codes_email_lower", func.lower(text("email"))),)

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    code_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, index=True
    )
