"""monthly reports

Revision ID: 20bf14fa3874
Revises: 876ab097ef1d
Create Date: 2026-11-25 11:07:25.732087

"""

import sqlalchemy as sa
from alembic import op

revision = "20bf14fa3874"
down_revision = "876ab097ef1d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monthly_reports",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "extract(day from month) = 1", name=op.f("monthly_reports_month_check")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("monthly_reports_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("monthly_reports_pkey")),
        sa.UniqueConstraint(
            "user_id", "month", name=op.f("monthly_reports_user_id_month_key")
        ),
    )
    op.create_index(
        op.f("ix_monthly_reports_created_at"),
        "monthly_reports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monthly_reports_deleted_at"),
        "monthly_reports",
        ["deleted_at"],
        unique=False,
    )
    op.add_column(
        "users",
        sa.Column(
            "receives_monthly_report",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "receives_monthly_report")
    op.drop_index(op.f("ix_monthly_reports_deleted_at"), table_name="monthly_reports")
    op.drop_index(op.f("ix_monthly_reports_created_at"), table_name="monthly_reports")
    op.drop_table("monthly_reports")
