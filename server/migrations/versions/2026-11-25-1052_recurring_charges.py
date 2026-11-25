"""recurring charges

Revision ID: 876ab097ef1d
Revises: c51550b994ba
Create Date: 2026-11-25 10:52:09.836052

"""

import sqlalchemy as sa
from alembic import op

revision = "876ab097ef1d"
down_revision = "c51550b994ba"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recurring_charges",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=16), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("day_of_month", sa.SmallInteger(), nullable=False),
        sa.Column("charged_through", sa.Date(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'credit card', 'debit card', 'withdrawal', 'check', 'wire', 'paypal')",
            name=op.f("recurring_charges_payment_method_check"),
        ),
        sa.CheckConstraint("amount > 0", name=op.f("recurring_charges_amount_check")),
        sa.CheckConstraint(
            "day_of_month BETWEEN 1 AND 31",
            name=op.f("recurring_charges_day_of_month_check"),
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("recurring_charges_property_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("recurring_charges_pkey")),
    )
    op.create_index(
        op.f("ix_recurring_charges_created_at"),
        "recurring_charges",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recurring_charges_deleted_at"),
        "recurring_charges",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recurring_charges_property_id"),
        "recurring_charges",
        ["property_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recurring_charges_property_id"), table_name="recurring_charges"
    )
    op.drop_index(
        op.f("ix_recurring_charges_deleted_at"), table_name="recurring_charges"
    )
    op.drop_index(
        op.f("ix_recurring_charges_created_at"), table_name="recurring_charges"
    )
    op.drop_table("recurring_charges")
