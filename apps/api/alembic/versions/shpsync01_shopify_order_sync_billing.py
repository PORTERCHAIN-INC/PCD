"""Shopify review 139170: order sync ledger + Shopify Billing API state."""

import sqlalchemy as sa
from alembic import op

revision = "shpsync01"
down_revision = "cp9flat01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, col in (
        ("billing_status", sa.String(32)),
        ("billing_subscription_gid", sa.String(128)),
        ("billing_usage_line_item_gid", sa.String(128)),
        ("billing_test", sa.Boolean()),
        ("billing_updated_at", sa.DateTime(timezone=True)),
        ("last_reconciled_at", sa.DateTime(timezone=True)),
    ):
        op.add_column("shopify_shops", sa.Column(name, col, nullable=True))
    op.create_table(
        "shopify_order_syncs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("merchant_id", sa.String(36), sa.ForeignKey("merchants.id"), nullable=False, index=True),
        sa.Column("shop_domain", sa.String(255), nullable=False),
        sa.Column("shopify_order_id", sa.String(64), nullable=False),
        sa.Column("order_name", sa.String(64)),
        sa.Column("status", sa.String(32), nullable=False, server_default="not_booked"),
        sa.Column("reason_code", sa.String(64)),
        sa.Column("is_test", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("financial_status", sa.String(32)),
        sa.Column("shipping_title", sa.String(255)),
        sa.Column("ship_to", sa.Text()),
        sa.Column("customer_name", sa.String(255)),
        sa.Column("line_items", sa.JSON()),
        sa.Column("currency", sa.String(8)),
        sa.Column("subtotal_cents", sa.Integer()),
        sa.Column("shipping_cents", sa.Integer()),
        sa.Column("total_cents", sa.Integer()),
        sa.Column("porterchain_order_id", sa.String(36)),
        sa.Column("source", sa.String(16), nullable=False, server_default="webhook"),
        sa.Column("shopify_created_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("shop_domain", "shopify_order_id", name="uq_shopify_order_sync"),
    )


def downgrade() -> None:
    op.drop_table("shopify_order_syncs")
    for name in ("last_reconciled_at", "billing_updated_at", "billing_test",
                 "billing_usage_line_item_gid", "billing_subscription_gid", "billing_status"):
        op.drop_column("shopify_shops", name)
