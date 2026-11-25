from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum, enum_check


class Role(StrEnum):
    owner = "owner"
    manager = "manager"
    homeowner = "homeowner"


class User(RecordModel):
    """Someone who can log in. Only owners add people: there is no sign-up."""

    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_email_lower",
            func.lower(text("email")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(enum_check("role", Role), name="role"),
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True, default=None)
    role: Mapped[Role] = mapped_column(StringEnum(Role, length=16), nullable=False)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    receives_monthly_report: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    """A homeowner emailed their properties' statements each month."""
