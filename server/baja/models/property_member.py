from uuid import UUID

from sqlalchemy import ForeignKey, Index, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from baja.kit.db.models import RecordModel

from .property import Property
from .user import User


class PropertyMember(RecordModel):
    """A homeowner's access to one property. Owners and managers see every property."""

    __tablename__ = "property_members"
    __table_args__ = (
        Index(
            "ix_property_members_user_property",
            "user_id",
            "property_id",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="cascade"), nullable=False, index=True
    )
    property_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("properties.id", ondelete="cascade"),
        nullable=False,
        index=True,
    )

    user: Mapped[User] = relationship(User, lazy="raise")
    property: Mapped[Property] = relationship(Property, lazy="raise")
