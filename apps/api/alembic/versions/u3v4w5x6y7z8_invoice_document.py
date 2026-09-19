"""P0b — invoice as a real AR document with lines and payment/ledger FKs."""

from alembic import op
import sqlalchemy as sa

revision = "u3v4w5x6y7z8"
down_revision = "t2u3v4w5x6y7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("status", sa.String(length=32), nullable=False, server_default="open"))
    op.add_column("invoices", sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_invoices_status", "invoices", ["status"])
    op.alter_column("invoices", "order_id", existing_type=sa.String(length=36), nullable=True)

    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("package_id", sa.String(length=36), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=False, server_default="Delivery"),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tax_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"]),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])
    op.create_index("ix_invoice_lines_order_id", "invoice_lines", ["order_id"])
    op.create_index("ix_invoice_lines_package_id", "invoice_lines", ["package_id"])

    op.add_column("payments", sa.Column("invoice_id", sa.String(length=36), nullable=True))
    op.create_index("ix_payments_invoice_id", "payments", ["invoice_id"])
    op.create_foreign_key("fk_payments_invoice_id", "payments", "invoices", ["invoice_id"], ["id"])
    op.execute(
        sa.text(
            """
            UPDATE payments p
            SET invoice_id = i.id
            FROM invoices i
            WHERE p.order_id IS NOT NULL AND i.order_id = p.order_id AND p.invoice_id IS NULL
            """
        )
    )

    op.add_column("billing_ledger_entries", sa.Column("invoice_id", sa.String(length=36), nullable=True))
    op.create_index("ix_billing_ledger_entries_invoice_id", "billing_ledger_entries", ["invoice_id"])
    op.create_foreign_key(
        "fk_billing_ledger_entries_invoice_id",
        "billing_ledger_entries",
        "invoices",
        ["invoice_id"],
        ["id"],
    )
    op.execute(
        sa.text(
            """
            UPDATE billing_ledger_entries e
            SET invoice_id = i.id
            FROM invoices i
            WHERE e.order_id IS NOT NULL AND i.order_id = e.order_id AND e.invoice_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            INSERT INTO invoice_lines (id, invoice_id, order_id, description, amount_cents, tax_cents)
            SELECT gen_random_uuid()::text, i.id, i.order_id, 'Delivery', i.amount_cents, COALESCE(i.tax_cents, 0)
            FROM invoices i
            WHERE NOT EXISTS (SELECT 1 FROM invoice_lines l WHERE l.invoice_id = i.id)
            """
        )
    )


def downgrade() -> None:
    op.drop_constraint("fk_billing_ledger_entries_invoice_id", "billing_ledger_entries", type_="foreignkey")
    op.drop_index("ix_billing_ledger_entries_invoice_id", table_name="billing_ledger_entries")
    op.drop_column("billing_ledger_entries", "invoice_id")
    op.drop_constraint("fk_payments_invoice_id", "payments", type_="foreignkey")
    op.drop_index("ix_payments_invoice_id", table_name="payments")
    op.drop_column("payments", "invoice_id")
    op.drop_index("ix_invoice_lines_package_id", table_name="invoice_lines")
    op.drop_index("ix_invoice_lines_order_id", table_name="invoice_lines")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    op.drop_index("ix_invoices_status", table_name="invoices")
    op.drop_column("invoices", "updated_at")
    op.drop_column("invoices", "voided_at")
    op.drop_column("invoices", "paid_at")
    op.drop_column("invoices", "issued_at")
    op.drop_column("invoices", "status")
    op.alter_column("invoices", "order_id", existing_type=sa.String(length=36), nullable=False)
