"""Merchant admin ops: owner, segments, credit hold, key rotation, documents, alerts.

Adds to `merchants`: `owner_admin_id`, `segment_tags`, `credit_hold_mode`
(none | manual | auto), `credit_hold_reason`, `credit_hold_at`,
`credit_override_until`. Adds `rotated_from_id` and `expires_at` to
`merchant_api_keys` so a rotated key keeps working for a grace window.
New tables `merchant_documents` (COI, signed contracts, tax forms; bytes
kept in Postgres, purged on erasure) and `merchant_alerts` (dedupe ledger for
churn / credit emails). All new columns are nullable or defaulted, so existing
rows read as "no owner, no hold".

Revision ID: ma0merchops1a2b
Revises: ib1cashtaxpay2b3c (integration chain)
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "ma0merchops1a2b"
down_revision = "ib1cashtaxpay2b3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("merchants") as t:
        t.add_column(sa.Column("owner_admin_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("segment_tags", sa.JSON(), nullable=True))
        t.add_column(
            sa.Column("credit_hold_mode", sa.String(16), nullable=False, server_default="none")
        )
        t.add_column(sa.Column("credit_hold_reason", sa.String(255), nullable=True))
        t.add_column(sa.Column("credit_hold_at", sa.DateTime(timezone=True), nullable=True))
        t.add_column(sa.Column("credit_override_until", sa.DateTime(timezone=True), nullable=True))
        t.create_check_constraint(
            "ck_merchants_credit_hold_mode", "credit_hold_mode IN ('none', 'manual', 'auto')"
        )
    op.create_index("ix_merchants_owner_admin_id", "merchants", ["owner_admin_id"])
    op.create_index("ix_merchants_credit_hold_mode", "merchants", ["credit_hold_mode"])

    with op.batch_alter_table("merchant_api_keys") as t:
        t.add_column(sa.Column("rotated_from_id", sa.String(36), nullable=True))
        t.add_column(sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "merchant_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(64), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=True),
        sa.Column("expires_on", sa.Date(), nullable=True),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("uploaded_by", sa.String(64), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_merchant_documents_merchant_id", "merchant_documents", ["merchant_id"])

    op.create_table(
        "merchant_alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="sent"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("merchant_id", "kind", "fingerprint", name="uq_merchant_alerts_dedupe"),
    )
    op.create_index("ix_merchant_alerts_merchant_id", "merchant_alerts", ["merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_merchant_alerts_merchant_id", table_name="merchant_alerts")
    op.drop_table("merchant_alerts")
    op.drop_index("ix_merchant_documents_merchant_id", table_name="merchant_documents")
    op.drop_table("merchant_documents")
    with op.batch_alter_table("merchant_api_keys") as t:
        t.drop_column("expires_at")
        t.drop_column("rotated_from_id")
    op.drop_index("ix_merchants_credit_hold_mode", table_name="merchants")
    op.drop_index("ix_merchants_owner_admin_id", table_name="merchants")
    with op.batch_alter_table("merchants") as t:
        t.drop_constraint("ck_merchants_credit_hold_mode", type_="check")
        t.drop_column("credit_override_until")
        t.drop_column("credit_hold_at")
        t.drop_column("credit_hold_reason")
        t.drop_column("credit_hold_mode")
        t.drop_column("segment_tags")
        t.drop_column("owner_admin_id")
