"""ledger

Revision ID: e775e346bb21
Revises: f0401e0d8def
Create Date: 2026-11-24 15:54:40.791229

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e775e346bb21"
down_revision = "f0401e0d8def"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transactions",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_method", sa.String(length=16), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("affects_balance", sa.Boolean(), nullable=False),
        sa.Column("entered_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "payment_method IN ('cash', 'credit card', 'debit card', 'withdrawal', 'check', 'wire', 'paypal')",
            name=op.f("transactions_payment_method_check"),
        ),
        sa.CheckConstraint(
            "type IN ('income', 'expense')", name=op.f("transactions_type_check")
        ),
        sa.CheckConstraint("amount > 0", name=op.f("transactions_amount_check")),
        sa.ForeignKeyConstraint(
            ["entered_by_id"],
            ["users.id"],
            name=op.f("transactions_entered_by_id_fkey"),
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("transactions_property_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("transactions_pkey")),
        sa.UniqueConstraint(
            "source", "external_id", name=op.f("transactions_source_external_id_key")
        ),
    )
    op.create_index(
        op.f("ix_transactions_created_at"), "transactions", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_transactions_deleted_at"), "transactions", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_transactions_property_date",
        "transactions",
        ["property_id", "date"],
        unique=False,
    )
    op.add_column(
        "properties",
        sa.Column(
            "balance_methods",
            postgresql.ARRAY(sa.String(length=16)),
            server_default=sa.text("'{cash}'"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        op.f("properties_balance_methods_check"),
        "properties",
        "balance_methods <@ ARRAY['cash', 'credit card', 'debit card', 'withdrawal', "
        "'check', 'wire', 'paypal']::varchar[]",
    )


def downgrade() -> None:
    op.drop_constraint(
        op.f("properties_balance_methods_check"), "properties", type_="check"
    )
    op.drop_column("properties", "balance_methods")
    op.drop_index("ix_transactions_property_date", table_name="transactions")
    op.drop_index(op.f("ix_transactions_deleted_at"), table_name="transactions")
    op.drop_index(op.f("ix_transactions_created_at"), table_name="transactions")
    op.drop_table("transactions")
