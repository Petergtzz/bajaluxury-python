"""invoices

Revision ID: 827148b3a986
Revises: 694fa5dd6e3c
Create Date: 2026-11-25 11:19:00.141811

"""

import sqlalchemy as sa
from alembic import op

revision = "827148b3a986"
down_revision = "694fa5dd6e3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "invoices",
        sa.Column("property_id", sa.Uuid(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("issued_on", sa.Date(), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=4), nullable=False),
        sa.Column("exchange_rate", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("payment_details", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=True),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint(
            "exchange_rate > 0", name=op.f("invoices_exchange_rate_check")
        ),
        sa.CheckConstraint("tax_rate >= 0", name=op.f("invoices_tax_rate_check")),
        sa.ForeignKeyConstraint(
            ["created_by_id"],
            ["users.id"],
            name=op.f("invoices_created_by_id_fkey"),
            ondelete="set null",
        ),
        sa.ForeignKeyConstraint(
            ["property_id"], ["properties.id"], name=op.f("invoices_property_id_fkey")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("invoices_pkey")),
        sa.UniqueConstraint(
            "year", "sequence", name=op.f("invoices_year_sequence_key")
        ),
    )
    op.create_index(
        op.f("ix_invoices_created_at"), "invoices", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_invoices_deleted_at"), "invoices", ["deleted_at"], unique=False
    )
    op.create_index(
        op.f("ix_invoices_property_id"), "invoices", ["property_id"], unique=False
    )
    op.create_table(
        "invoice_lines",
        sa.Column("invoice_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("guest_expense_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("modified_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.CheckConstraint("quantity > 0", name=op.f("invoice_lines_quantity_check")),
        sa.CheckConstraint(
            "unit_price >= 0", name=op.f("invoice_lines_unit_price_check")
        ),
        sa.ForeignKeyConstraint(
            ["guest_expense_id"],
            ["guest_expenses.id"],
            name=op.f("invoice_lines_guest_expense_id_fkey"),
        ),
        sa.ForeignKeyConstraint(
            ["invoice_id"],
            ["invoices.id"],
            name=op.f("invoice_lines_invoice_id_fkey"),
            ondelete="cascade",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("invoice_lines_pkey")),
    )
    op.create_index(
        op.f("ix_invoice_lines_created_at"),
        "invoice_lines",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoice_lines_deleted_at"),
        "invoice_lines",
        ["deleted_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoice_lines_guest_expense_id"),
        "invoice_lines",
        ["guest_expense_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_invoice_lines_invoice_id"),
        "invoice_lines",
        ["invoice_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_invoice_lines_invoice_id"), table_name="invoice_lines")
    op.drop_index(op.f("ix_invoice_lines_guest_expense_id"), table_name="invoice_lines")
    op.drop_index(op.f("ix_invoice_lines_deleted_at"), table_name="invoice_lines")
    op.drop_index(op.f("ix_invoice_lines_created_at"), table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index(op.f("ix_invoices_property_id"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_deleted_at"), table_name="invoices")
    op.drop_index(op.f("ix_invoices_created_at"), table_name="invoices")
    op.drop_table("invoices")
