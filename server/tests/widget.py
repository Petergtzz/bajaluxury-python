from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel


class Widget(RecordModel):
    """A test-only table, for testing the plumbing without a real domain."""

    __tablename__ = "widgets"

    name: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
