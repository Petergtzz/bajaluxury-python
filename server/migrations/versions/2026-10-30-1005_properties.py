"""properties

Revision ID: f0401e0d8def
Revises: 5381388f505d
Create Date: 2026-10-30 10:05:41.276979

"""

import sqlalchemy as sa
from alembic import op

revision = "f0401e0d8def"
down_revision = "5381388f505d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("is_archived", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("properties_pkey")),
    )
    op.create_index(
        op.f("ix_properties_created_at"), "properties", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_properties_deleted_at"), "properties", ["deleted_at"], unique=False
    )
    op.create_index(
        "ix_properties_name_lower",
        "properties",
        [sa.literal_column("lower(name)")],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_table(
        "property_members",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["property_id"],
            ["properties.id"],
            name=op.f("property_members_property_id_fkey"),
            ondelete="cascade",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("property_members_user_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("property_members_pkey")),
    )
    op.create_index(
        op.f("ix_property_members_created_at"),
        "property_members",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_members_deleted_at"),
        "property_members",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_members_property_id"),
        "property_members",
        ["property_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_property_members_user_id"),
        "property_members",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_property_members_user_property",
        "property_members",
        ["user_id", "property_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_property_members_user_property",
        table_name="property_members",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_property_members_user_id"), table_name="property_members")
    op.drop_index(
        op.f("ix_property_members_property_id"), table_name="property_members"
    )
    op.drop_index(op.f("ix_property_members_deleted_at"), table_name="property_members")
    op.drop_index(op.f("ix_property_members_created_at"), table_name="property_members")
    op.drop_table("property_members")
    op.drop_index(
        "ix_properties_name_lower",
        table_name="properties",
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.drop_index(op.f("ix_properties_deleted_at"), table_name="properties")
    op.drop_index(op.f("ix_properties_created_at"), table_name="properties")
    op.drop_table("properties")
