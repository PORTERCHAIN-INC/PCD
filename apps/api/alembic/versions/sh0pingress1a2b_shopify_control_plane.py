"""Shopify admin control plane: pause, auto_dispatch, ingress DLQ.

Revision ID: sh0pingress1a2b
Revises: tx0hstfuel1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "sh0pingress1a2b"
down_revision = "tx0hstfuel1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_shops",
        sa.Column("ingress_paused", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "shopify_shops",
        sa.Column("auto_dispatch", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_shopify_shops_ingress_paused", "shopify_shops", ["ingress_paused"])

    op.create_table(
        "shopify_ingress_dlq",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("merchant_id", sa.String(length=36), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("shop_id", sa.String(length=36), sa.ForeignKey("shopify_shops.id"), nullable=True),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=128), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("shopify_order_id", sa.String(length=64), nullable=True),
        sa.Column("reason_code", sa.String(length=64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("raw_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("porterchain_order_id", sa.String(length=36), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by_admin_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shopify_ingress_dlq_merchant_id", "shopify_ingress_dlq", ["merchant_id"])
    op.create_index("ix_shopify_ingress_dlq_shop_id", "shopify_ingress_dlq", ["shop_id"])
    op.create_index("ix_shopify_ingress_dlq_status", "shopify_ingress_dlq", ["status"])
    op.create_index(
        "ix_shopify_ingress_dlq_shopify_order_id", "shopify_ingress_dlq", ["shopify_order_id"]
    )
    op.create_index("ix_shopify_ingress_dlq_created_at", "shopify_ingress_dlq", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_shopify_ingress_dlq_created_at", table_name="shopify_ingress_dlq")
    op.drop_index("ix_shopify_ingress_dlq_shopify_order_id", table_name="shopify_ingress_dlq")
    op.drop_index("ix_shopify_ingress_dlq_status", table_name="shopify_ingress_dlq")
    op.drop_index("ix_shopify_ingress_dlq_shop_id", table_name="shopify_ingress_dlq")
    op.drop_index("ix_shopify_ingress_dlq_merchant_id", table_name="shopify_ingress_dlq")
    op.drop_table("shopify_ingress_dlq")
    op.drop_index("ix_shopify_shops_ingress_paused", table_name="shopify_shops")
    op.drop_column("shopify_shops", "auto_dispatch")
    op.drop_column("shopify_shops", "ingress_paused")
