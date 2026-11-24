from datetime import datetime
from uuid import UUID

from sqlalchemy import TIMESTAMP, MetaData, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from baja.kit.utils import generate_uuid, utc_now

metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_N_label)s",
        "uq": "%(table_name)s_%(column_0_N_name)s_key",
        "ck": "%(table_name)s_%(constraint_name)s_check",
        "fk": "%(table_name)s_%(column_0_N_name)s_fkey",
        "pk": "%(table_name)s_pkey",
    }
)


class Model(DeclarativeBase):
    __abstract__ = True
    metadata = metadata


class RecordModel(Model):
    """A row with an id, timestamps and soft deletion: every table but join tables."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=generate_uuid)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, default=utc_now, index=True
    )
    modified_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None, onupdate=utc_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True, default=None, index=True
    )

    def __eq__(self, value: object, /) -> bool:
        return isinstance(value, self.__class__) and self.id == value.id

    def __hash__(self) -> int:
        return self.id.int
