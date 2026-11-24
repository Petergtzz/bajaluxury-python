"""accounts

Revision ID: 5381388f505d
Revises:
Create Date: 2026-10-24 10:29:29.032592

"""

import sqlalchemy as sa
from alembic import op

revision = "5381388f505d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("timezone", sa.String(length=64), nullable=False),
        sa.Column(
            "usd_exchange_rate", sa.Numeric(precision=10, scale=4), nullable=False
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "currency IN ('MXN', 'USD')", name=op.f("companies_currency_check")
        ),
        sa.CheckConstraint(
            "usd_exchange_rate > 0", name=op.f("companies_usd_exchange_rate_check")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("companies_pkey")),
    )
    op.create_index(
        op.f("ix_companies_created_at"), "companies", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_companies_deleted_at"), "companies", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_companies_singleton",
        "companies",
        [sa.literal_column("(true)")],
        unique=True,
    )
    op.create_table(
        "login_codes",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("code_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("login_codes_pkey")),
    )
    op.create_index(
        op.f("ix_login_codes_created_at"), "login_codes", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_login_codes_deleted_at"), "login_codes", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_login_codes_email_lower",
        "login_codes",
        [sa.literal_column("lower(email)")],
        unique=False,
    )
    op.create_index(
        op.f("ix_login_codes_expires_at"), "login_codes", ["expires_at"], unique=False
    )
    op.create_table(
        "users",
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "role IN ('owner', 'manager', 'homeowner')", name=op.f("users_role_check")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("users_pkey")),
    )
    op.create_index(op.f("ix_users_created_at"), "users", ["created_at"], unique=False)
    op.create_index(op.f("ix_users_deleted_at"), "users", ["deleted_at"], unique=False)
    op.create_index(
        "ix_users_email_lower",
        "users",
        [sa.literal_column("lower(email)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "user_sessions",
        sa.Column("token", sa.CHAR(length=64), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("user_agent", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("user_sessions_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("user_sessions_pkey")),
        sa.UniqueConstraint("token", name=op.f("user_sessions_token_key")),
    )
    op.create_index(
        op.f("ix_user_sessions_created_at"),
        "user_sessions",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_deleted_at"),
        "user_sessions",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_expires_at"),
        "user_sessions",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_deleted_at"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_created_at"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(
        "ix_users_email_lower",
        table_name="users",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_users_deleted_at"), table_name="users")
    op.drop_index(op.f("ix_users_created_at"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_login_codes_expires_at"), table_name="login_codes")
    op.drop_index("ix_login_codes_email_lower", table_name="login_codes")
    op.drop_index(op.f("ix_login_codes_deleted_at"), table_name="login_codes")
    op.drop_index(op.f("ix_login_codes_created_at"), table_name="login_codes")
    op.drop_table("login_codes")
    op.drop_index("ix_companies_singleton", table_name="companies")
    op.drop_index(op.f("ix_companies_deleted_at"), table_name="companies")
    op.drop_index(op.f("ix_companies_created_at"), table_name="companies")
    op.drop_table("companies")
