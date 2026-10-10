"""Interac e-Transfer billing: invoice reference + partial payments, cycle invoices,
gap-free invoice sequence, inbound Interac transfer review queue.

Existing invoices stay valid: new columns are nullable or defaulted, `billing_kind`
reads "order" for every legacy row, and old random invoice numbers are untouched.

Revision ID: ib0interacbill1a2b
Revises: cf1custr2b3c4 (integration chain)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ib0interacbill1a2b"
down_revision = "cf1custr2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("payment_reference", sa.String(16), nullable=True))
    op.create_index("ix_invoices_payment_reference", "invoices", ["payment_reference"], unique=True)
    op.add_column(
        "invoices",
        sa.Column("amount_paid_cents", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "invoices",
        sa.Column("billing_kind", sa.String(16), nullable=False, server_default="order"),
    )

    op.create_table(
        "invoice_number_sequences",
        sa.Column("scope", sa.String(32), primary_key=True),
        sa.Column("last_value", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "interac_transfers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("message_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="notification"),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("sender_email", sa.String(255), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="cad"),
        sa.Column("memo", sa.String(512), nullable=True),
        sa.Column("interac_reference", sa.String(64), nullable=True),
        sa.Column("auth_ok", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auth_detail", sa.String(255), nullable=True),
        sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=True),
        sa.Column("merchant_id", sa.String(36), nullable=True),
        sa.Column("match_method", sa.String(32), nullable=True),
        sa.Column("match_note", sa.String(255), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="needs_review"),
        sa.Column("payment_id", sa.String(36), nullable=True),
        sa.Column("reviewed_by", sa.String(128), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_interac_transfers_message_id", "interac_transfers", ["message_id"], unique=True)
    op.create_index("ix_interac_transfers_status", "interac_transfers", ["status"])
    op.create_index("ix_interac_transfers_invoice_id", "interac_transfers", ["invoice_id"])
    op.create_index("ix_interac_transfers_merchant_id", "interac_transfers", ["merchant_id"])
    op.create_index("ix_interac_transfers_interac_reference", "interac_transfers", ["interac_reference"])


def downgrade() -> None:
    op.drop_table("interac_transfers")
    op.drop_table("invoice_number_sequences")
    op.drop_column("invoices", "billing_kind")
    op.drop_column("invoices", "amount_paid_cents")
    op.drop_index("ix_invoices_payment_reference", table_name="invoices")
    op.drop_column("invoices", "payment_reference")
