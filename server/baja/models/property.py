from sqlalchemy import Boolean, CheckConstraint, Index, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from baja.kit.db.models import RecordModel
from baja.kit.extensions.sqlalchemy import StringEnum

from .transaction import PaymentMethod


class Property(RecordModel):
    """A home under management. Archived ones keep their history but take no new work."""

    __tablename__ = "properties"
    __table_args__ = (
        Index(
            "ix_properties_name_lower",
            func.lower(text("name")),
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
        CheckConstraint(
            "balance_methods <@ ARRAY[{}]::varchar[]".format(
                ", ".join(f"'{method.value}'" for method in PaymentMethod)
            ),
            name="balance_methods",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(
        String(500), nullable=True, default=None
    )
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    balance_methods: Mapped[list[PaymentMethod]] = mapped_column(
        ARRAY(StringEnum(PaymentMethod, length=16)),
        nullable=False,
        default=lambda: [PaymentMethod.cash],
        server_default=text("'{cash}'"),
    )
    """
    The payment methods whose expenses come out of the owner's balance with us.

    Usually cash: the rest is paid from the owner's own cards and accounts.
    Replace the list rather than mutating it, or the change is not saved.
    """
