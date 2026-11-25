"""property reports

Revision ID: 653a4d229149
Revises: 827148b3a986
Create Date: 2026-11-25 12:19:26.183154

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "653a4d229149"
down_revision = "827148b3a986"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_reports",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("send_day", sa.SmallInteger(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "send_day BETWEEN 1 AND 28", name=op.f("property_reports_send_day_check")
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("property_reports_property_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("property_reports_pkey")),
    )
    op.create_index(
        op.f("ix_property_reports_created_at"),
        "property_reports",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_reports_deleted_at"),
        "property_reports",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        "ix_property_reports_property",
        "property_reports",
        ["property_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "report_sends",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("month", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=8), nullable=False),
        sa.Column(
            "to_addresses", postgresql.ARRAY(sa.String(length=320)), nullable=False
        ),
        sa.Column(
            "cc_addresses", postgresql.ARRAY(sa.String(length=320)), nullable=False
        ),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("error", sa.String(length=500), nullable=True),
        sa.Column("statement", sa.LargeBinary(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'sent', 'failed')",
            name=op.f("report_sends_status_check"),
        ),
        sa.CheckConstraint(
            "extract(day from month) = 1", name=op.f("report_sends_month_check")
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("report_sends_property_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("report_sends_pkey")),
    )
    op.create_index(
        op.f("ix_report_sends_created_at"), "report_sends", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_report_sends_deleted_at"), "report_sends", ["deleted_at"], unique=False
    )
    op.create_index(
        op.f("ix_report_sends_property_id"),
        "report_sends",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        "ix_report_sends_property_month",
        "report_sends",
        ["property_id", "month"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "property_report_recipients",
        sa.Column("property_report_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('to', 'cc')", name=op.f("property_report_recipients_kind_check")
        ),
        sa.ForeignKeyConstraint(
            ["property_report_id"],
            ["property_reports.id"],
            name=op.f("property_report_recipients_property_report_id_fkey"),
            ondelete="cascade",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("property_report_recipients_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("property_report_recipients_pkey")),
    )
    op.create_index(
        op.f("ix_property_report_recipients_created_at"),
        "property_report_recipients",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_report_recipients_deleted_at"),
        "property_report_recipients",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_report_recipients_property_report_id"),
        "property_report_recipients",
        ["property_report_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_report_recipients_report_user",
        "property_report_recipients",
        ["property_report_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        op.f("ix_property_report_recipients_user_id"),
        "property_report_recipients",
        ["user_id"],
        unique=False,
    )
    # Who got the monthly report per person becomes who receives each
    # property's report: a homeowner, addressed, on the 2nd, as Laravel planned.
    op.execute(
        """
        INSERT INTO property_reports (id, property_id, send_day, created_at)
        SELECT gen_random_uuid(), m.property_id, 2, now()
        FROM property_members m
        JOIN users u ON u.id = m.user_id
        JOIN properties p ON p.id = m.property_id
        WHERE u.receives_monthly_report AND u.role = 'homeowner'
          AND u.deleted_at IS NULL AND m.deleted_at IS NULL
          AND p.deleted_at IS NULL AND NOT p.is_archived
        GROUP BY m.property_id
        """
    )
    op.execute(
        """
        INSERT INTO property_report_recipients
            (id, property_report_id, user_id, kind, created_at)
        SELECT gen_random_uuid(), r.id, m.user_id, 'to', now()
        FROM property_reports r
        JOIN property_members m
            ON m.property_id = r.property_id AND m.deleted_at IS NULL
        JOIN users u ON u.id = m.user_id
        WHERE u.receives_monthly_report AND u.role = 'homeowner'
          AND u.deleted_at IS NULL
        """
    )
    op.drop_index(op.f("ix_monthly_reports_created_at"), table_name="monthly_reports")
    op.drop_index(op.f("ix_monthly_reports_deleted_at"), table_name="monthly_reports")
    op.drop_table("monthly_reports")
    op.drop_column("users", "receives_monthly_report")


def downgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "receives_monthly_report",
            sa.BOOLEAN(),
            server_default=sa.text("false"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.create_table(
        "monthly_reports",
        sa.Column("user_id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column("month", sa.DATE(), autoincrement=False, nullable=False),
        sa.Column(
            "sent_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column("id", sa.UUID(), autoincrement=False, nullable=False),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.Column(
            "deleted_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
        sa.CheckConstraint(
            "EXTRACT(day FROM month) = 1::numeric",
            name=op.f("monthly_reports_month_check"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("monthly_reports_user_id_fkey"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("monthly_reports_pkey")),
        sa.UniqueConstraint(
            "user_id",
            "month",
            name=op.f("monthly_reports_user_id_month_key"),
            postgresql_include=[],
            postgresql_nulls_not_distinct=False,
        ),
    )
    op.create_index(
        op.f("ix_monthly_reports_deleted_at"),
        "monthly_reports",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monthly_reports_created_at"),
        "monthly_reports",
        ["created_at"],
        unique=False,
    )
    op.drop_index(
        op.f("ix_property_report_recipients_user_id"),
        table_name="property_report_recipients",
    )
    op.drop_index(
        "ix_property_report_recipients_report_user",
        table_name="property_report_recipients",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_property_report_recipients_property_report_id"),
        table_name="property_report_recipients",
    )
    op.drop_index(
        op.f("ix_property_report_recipients_deleted_at"),
        table_name="property_report_recipients",
    )
    op.drop_index(
        op.f("ix_property_report_recipients_created_at"),
        table_name="property_report_recipients",
    )
    op.drop_table("property_report_recipients")
    op.drop_index(
        "ix_report_sends_property_month",
        table_name="report_sends",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_report_sends_property_id"), table_name="report_sends")
    op.drop_index(op.f("ix_report_sends_deleted_at"), table_name="report_sends")
    op.drop_index(op.f("ix_report_sends_created_at"), table_name="report_sends")
    op.drop_table("report_sends")
    op.drop_index(
        "ix_property_reports_property",
        table_name="property_reports",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_property_reports_deleted_at"), table_name="property_reports")
    op.drop_index(op.f("ix_property_reports_created_at"), table_name="property_reports")
    op.drop_table("property_reports")
