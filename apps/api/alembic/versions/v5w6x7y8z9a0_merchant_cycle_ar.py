"""Merchant cycle AR — nullable invoice.customer_id, merchant_id, due_at, period; payments.quote_id nullable."""

from alembic import op
import sqlalchemy as sa

revision = "v5w6x7y8z9a0"
down_revision = "u4v5w6x7y8z9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("invoices", "customer_id", existing_type=sa.String(length=36), nullable=True)
    op.add_column("invoices", sa.Column("merchant_id", sa.String(length=36), nullable=True))
    op.add_column("invoices", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("billing_period_start", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("billing_period_end", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_invoices_merchant_id", "invoices", ["merchant_id"])
    op.create_foreign_key(
        "fk_invoices_merchant_id_merchants",
        "invoices",
        "merchants",
        ["merchant_id"],
        ["id"],
    )

    op.alter_column("payments", "quote_id", existing_type=sa.String(length=36), nullable=True)


def downgrade() -> None:
    op.alter_column("payments", "quote_id", existing_type=sa.String(length=36), nullable=False)
    op.drop_constraint("fk_invoices_merchant_id_merchants", "invoices", type_="foreignkey")
    op.drop_index("ix_invoices_merchant_id", table_name="invoices")
    op.drop_column("invoices", "billing_period_end")
    op.drop_column("invoices", "billing_period_start")
    op.drop_column("invoices", "due_at")
    op.drop_column("invoices", "merchant_id")
    op.alter_column("invoices", "customer_id", existing_type=sa.String(length=36), nullable=False)
