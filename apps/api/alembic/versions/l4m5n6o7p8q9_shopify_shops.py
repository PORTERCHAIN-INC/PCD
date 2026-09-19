"""Shopify shops + postal on saved pickup addresses."""

from alembic import op
import sqlalchemy as sa

revision = "l4m5n6o7p8q9"
down_revision = "k3l4m5n6o7p8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("saved_addresses", sa.Column("postal", sa.String(length=16), nullable=True))
    op.create_table(
        "shopify_shops",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("merchant_id", sa.String(length=36), sa.ForeignKey("merchants.id"), nullable=False),
        sa.Column("shop_domain", sa.String(length=255), nullable=False),
        sa.Column("encrypted_access_token", sa.Text(), nullable=True),
        sa.Column("encrypted_webhook_secret", sa.String(length=512), nullable=True),
        sa.Column("default_pickup_address_id", sa.String(length=36), sa.ForeignKey("saved_addresses.id"), nullable=True),
        sa.Column("shopify_shop_gid", sa.String(length=128), nullable=True),
        sa.Column("scopes", sa.String(length=512), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uninstalled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_webhook_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_shopify_shops_merchant_id", "shopify_shops", ["merchant_id"])
    op.create_index("ix_shopify_shops_shop_domain", "shopify_shops", ["shop_domain"])
    op.create_index("uq_shopify_shops_shop_domain", "shopify_shops", ["shop_domain"], unique=True)
    op.create_index(
        "ix_shopify_shops_default_pickup_address_id",
        "shopify_shops",
        ["default_pickup_address_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_shopify_shops_default_pickup_address_id", table_name="shopify_shops")
    op.drop_index("uq_shopify_shops_shop_domain", table_name="shopify_shops")
    op.drop_index("ix_shopify_shops_shop_domain", table_name="shopify_shops")
    op.drop_index("ix_shopify_shops_merchant_id", table_name="shopify_shops")
    op.drop_table("shopify_shops")
    op.drop_column("saved_addresses", "postal")
