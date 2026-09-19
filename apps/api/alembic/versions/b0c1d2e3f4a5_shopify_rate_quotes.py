"""Shopify rate quotes for CarrierService → book reconciliation (Quote≡Book)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "b0c1d2e3f4a5"
down_revision = "a9b0c1d2e3f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shopify_rate_quotes",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("shop_id", sa.String(length=36), sa.ForeignKey("shopify_shops.id"), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("total_cents", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False, server_default="CAD"),
        sa.Column("breakdown", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("pickup_postal", sa.String(length=32), nullable=True),
        sa.Column("dropoff_postal", sa.String(length=32), nullable=True),
        sa.Column("weight_kg", sa.String(length=32), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_shopify_rate_quotes_shop_id", "shopify_rate_quotes", ["shop_id"])
    op.create_index("ix_shopify_rate_quotes_merchant_id", "shopify_rate_quotes", ["merchant_id"])
    op.create_index("ix_shopify_rate_quotes_request_hash", "shopify_rate_quotes", ["request_hash"])
    op.create_index("ix_shopify_rate_quotes_expires_at", "shopify_rate_quotes", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_shopify_rate_quotes_expires_at", table_name="shopify_rate_quotes")
    op.drop_index("ix_shopify_rate_quotes_request_hash", table_name="shopify_rate_quotes")
    op.drop_index("ix_shopify_rate_quotes_merchant_id", table_name="shopify_rate_quotes")
    op.drop_index("ix_shopify_rate_quotes_shop_id", table_name="shopify_rate_quotes")
    op.drop_table("shopify_rate_quotes")
