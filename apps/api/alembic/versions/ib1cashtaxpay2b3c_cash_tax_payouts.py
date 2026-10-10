"""Billing round 2: province tax on invoices, reminder drafts, Stripe payouts,
driver payout runs.

Existing rows stay valid: every new column is nullable.

Revision ID: ib1cashtaxpay2b3c
Revises: ib0interacbill1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ib1cashtaxpay2b3c"
down_revision = "ib0interacbill1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("tax_province", sa.String(2), nullable=True))
    op.add_column("invoice_lines", sa.Column("tax_province", sa.String(2), nullable=True))

    op.create_table(
        "finance_reminder_drafts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("merchant_id", sa.String(36), nullable=False, index=True),
        sa.Column("invoice_ids", sa.JSON(), nullable=False),
        sa.Column("to_email", sa.String(320), nullable=True),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("oldest_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft", index=True),
        sa.Column("decided_by", sa.String(128), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "stripe_payouts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("stripe_payout_id", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(8), nullable=False, server_default="cad"),
        sa.Column("arrival_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("gross_cents", sa.Integer(), nullable=True),
        sa.Column("fee_cents", sa.Integer(), nullable=True),
        sa.Column("refund_cents", sa.Integer(), nullable=True),
        sa.Column("dispute_cents", sa.Integer(), nullable=True),
        sa.Column("other_cents", sa.Integer(), nullable=True),
        sa.Column("matched_count", sa.Integer(), nullable=True),
        sa.Column("unmatched_count", sa.Integer(), nullable=True),
        sa.Column("difference_cents", sa.Integer(), nullable=True),
        sa.Column("reconciled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "driver_payout_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft", index=True),
        sa.Column("lines", sa.JSON(), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("driver_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("approved_by", sa.String(128), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by", sa.String(128), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("driver_payout_runs")
    op.drop_table("stripe_payouts")
    op.drop_table("finance_reminder_drafts")
    op.drop_column("invoice_lines", "tax_province")
    op.drop_column("invoices", "tax_province")
