"""guest expenses and api tokens

Revision ID: c51550b994ba
Revises: e775e346bb21
Create Date: 2026-11-24 16:08:05.833203

"""

import sqlalchemy as sa
from alembic import op

revision = "c51550b994ba"
down_revision = "e775e346bb21"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_tokens",
        sa.Column("token", sa.CHAR(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("last_used_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("api_tokens_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("api_tokens_pkey")),
        sa.UniqueConstraint("token", name=op.f("api_tokens_token_key")),
    )
    op.create_index(
        op.f("ix_api_tokens_created_at"), "api_tokens", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_api_tokens_deleted_at"), "api_tokens", ["deleted_at"], unique=False
    )
    op.create_index(
        op.f("ix_api_tokens_user_id"), "api_tokens", ["user_id"], unique=False
    )
    op.create_table(
        "guest_expenses",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("concept", sa.String(length=255), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("entered_by_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("amount > 0", name=op.f("guest_expenses_amount_check")),
        sa.ForeignKeyConstraint(
            ["entered_by_id"],
            ["users.id"],
            name=op.f("guest_expenses_entered_by_id_fkey"),
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("guest_expenses_property_id_fkey"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("guest_expenses_pkey")),
        sa.UniqueConstraint(
            "source", "external_id", name=op.f("guest_expenses_source_external_id_key")
        ),
    )
    op.create_index(
        op.f("ix_guest_expenses_created_at"),
        "guest_expenses",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_guest_expenses_deleted_at"),
        "guest_expenses",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_guest_expenses_property_date",
        "guest_expenses",
        ["property_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_guest_expenses_property_date", table_name="guest_expenses")
    op.drop_index(op.f("ix_guest_expenses_deleted_at"), table_name="guest_expenses")
    op.drop_index(op.f("ix_guest_expenses_created_at"), table_name="guest_expenses")
    op.drop_table("guest_expenses")
    op.drop_index(op.f("ix_api_tokens_user_id"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_deleted_at"), table_name="api_tokens")
    op.drop_index(op.f("ix_api_tokens_created_at"), table_name="api_tokens")
    op.drop_table("api_tokens")
