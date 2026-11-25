"""checklists

Revision ID: 694fa5dd6e3c
Revises: 20bf14fa3874
Create Date: 2026-11-25 11:12:14.753738

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "694fa5dd6e3c"
down_revision = "20bf14fa3874"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "checklist_template_items",
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('check_in', 'check_out', 'weekly')",
            name=op.f("checklist_template_items_type_check"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("checklist_template_items_pkey")),
    )
    op.create_index(
        op.f("ix_checklist_template_items_created_at"),
        "checklist_template_items",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_template_items_deleted_at"),
        "checklist_template_items",
        ["deleted_at"],
        unique=False,
    )
    op.create_table(
        "checklists",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "emailed_to",
            postgresql.ARRAY(sa.String(length=320)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "type IN ('check_in', 'check_out', 'weekly')",
            name=op.f("checklists_type_check"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("checklists_created_by_id_fkey"),
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"], ["properties.id"], name=op.f("checklists_property_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("checklists_pkey")),
    )
    op.create_index(
        op.f("ix_checklists_created_at"), "checklists", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_checklists_deleted_at"), "checklists", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_checklists_property_created",
        "checklists",
        ["property_id", "created_at"],
        unique=False,
    )
    op.create_table(
        "checklist_items",
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("is_checked", sa.Boolean(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["checklist_id"],
            ["checklists.id"],
            name=op.f("checklist_items_checklist_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("checklist_items_pkey")),
    )
    op.create_index(
        op.f("ix_checklist_items_checklist_id"),
        "checklist_items",
        ["checklist_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_items_created_at"),
        "checklist_items",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_checklist_items_deleted_at"),
        "checklist_items",
        ["deleted_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_checklist_items_deleted_at"), table_name="checklist_items")
    op.drop_index(op.f("ix_checklist_items_created_at"), table_name="checklist_items")
    op.drop_index(op.f("ix_checklist_items_checklist_id"), table_name="checklist_items")
    op.drop_table("checklist_items")
    op.drop_index("ix_checklists_property_created", table_name="checklists")
    op.drop_index(op.f("ix_checklists_deleted_at"), table_name="checklists")
    op.drop_index(op.f("ix_checklists_created_at"), table_name="checklists")
    op.drop_table("checklists")
    op.drop_index(
        op.f("ix_checklist_template_items_deleted_at"),
        table_name="checklist_template_items",
    )
    op.drop_index(
        op.f("ix_checklist_template_items_created_at"),
        table_name="checklist_template_items",
    )
    op.drop_table("checklist_template_items")
