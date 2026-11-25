"""checklist recipients

Revision ID: ab76b40df9b0
Revises: 653a4d229149
Create Date: 2026-11-25 13:05:34.788236

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "ab76b40df9b0"
down_revision = "653a4d229149"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_recipients",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=2), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "kind IN ('to', 'cc')", name=op.f("checklist_recipients_kind_check")
        ),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("checklist_recipients_property_id_fkey"),
            ondelete="cascade",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("checklist_recipients_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("checklist_recipients_pkey")),
    )
    op.create_index(
        op.f("ix_checklist_recipients_created_at"),
        "checklist_recipients",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_recipients_deleted_at"),
        "checklist_recipients",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_recipients_property_id"),
        "checklist_recipients",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        "ix_checklist_recipients_property_user",
        "checklist_recipients",
        ["property_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        op.f("ix_checklist_recipients_user_id"),
        "checklist_recipients",
        ["user_id"],
        unique=False,
    )
    op.add_column(
        "checklists",
        sa.Column(
            "emailed_cc",
            postgresql.ARRAY(sa.String(length=320)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )

    # Laravel offered a house's homeowners as a checklist's recipients; they are
    # who each active house's checklists now go to, until someone changes it.
    op.execute(
        """
        INSERT INTO checklist_recipients (id, property_id, user_id, kind, created_at)
        SELECT gen_random_uuid(), m.property_id, m.user_id, 'to', now()
        FROM property_members m
        JOIN properties p ON p.id = m.property_id
        JOIN users u ON u.id = m.user_id
        WHERE m.deleted_at IS NULL AND p.deleted_at IS NULL AND NOT p.is_archived
          AND u.deleted_at IS NULL AND u.role = 'homeowner'
        """
    )


def downgrade() -> None:
    op.drop_column("checklists", "emailed_cc")
    op.drop_index(
        op.f("ix_checklist_recipients_user_id"), table_name="checklist_recipients"
    )
    op.drop_index(
        "ix_checklist_recipients_property_user",
        table_name="checklist_recipients",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(
        op.f("ix_checklist_recipients_property_id"), table_name="checklist_recipients"
    )
    op.drop_index(
        op.f("ix_checklist_recipients_deleted_at"), table_name="checklist_recipients"
    )
    op.drop_index(
        op.f("ix_checklist_recipients_created_at"), table_name="checklist_recipients"
    )
    op.drop_table("checklist_recipients")
