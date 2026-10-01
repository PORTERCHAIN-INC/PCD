"""Shopify buyer privacy request cases.

Revision ID: pr0shopdsr1a2b
Revises: sh2gqlids3c4d
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "pr0shopdsr1a2b"
down_revision = "sh2gqlids3c4d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopify_data_subject_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shop_id", sa.String(length=36), nullable=True),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("topic", sa.String(length=64), nullable=False),
        sa.Column("shopify_webhook_id", sa.String(length=128), nullable=False),
        sa.Column("shopify_customer_id", sa.String(length=64), nullable=True),
        sa.Column("email_hash", sa.String(length=64), nullable=True),
        sa.Column("phone_hash", sa.String(length=64), nullable=True),
        sa.Column("orders_requested", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("export_ciphertext", sa.Text(), nullable=True),
        sa.Column("orders_touched", sa.Integer(), nullable=False),
        sa.Column("hold_reason", sa.String(length=32), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["shopify_shops.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shopify_webhook_id", name="uq_shopify_dsr_webhook_id"),
    )
    op.create_index("ix_shopify_dsr_shop_id", "shopify_data_subject_requests", ["shop_id"])
    op.create_index("ix_shopify_dsr_merchant_id", "shopify_data_subject_requests", ["merchant_id"])
    op.create_index("ix_shopify_dsr_topic", "shopify_data_subject_requests", ["topic"])
    op.create_index("ix_shopify_dsr_status", "shopify_data_subject_requests", ["status"])


def downgrade() -> None:
    op.drop_index("ix_shopify_dsr_status", table_name="shopify_data_subject_requests")
    op.drop_index("ix_shopify_dsr_topic", table_name="shopify_data_subject_requests")
    op.drop_index("ix_shopify_dsr_merchant_id", table_name="shopify_data_subject_requests")
    op.drop_index("ix_shopify_dsr_shop_id", table_name="shopify_data_subject_requests")
    op.drop_table("shopify_data_subject_requests")
