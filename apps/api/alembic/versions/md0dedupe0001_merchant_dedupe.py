"""merchant dedupe: merchant_merges + unique normalized HST/GST number.

shopify_shops.shop_domain is already unique (uq_shopify_shops_shop_domain).
Prod checked 2026-10-15 (read-only): no duplicate HST numbers among live merchants.
"""

import sqlalchemy as sa
from alembic import op

revision = "md0dedupe0001"
down_revision = "sd0softdel0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "merchant_merges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_merchant_id", sa.String(36), nullable=False, index=True),
        sa.Column("target_merchant_id", sa.String(36), nullable=False, index=True),
        sa.Column("actor", sa.String(128)),
        sa.Column("moved", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(16), nullable=False, server_default="merged"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("undone_at", sa.DateTime(timezone=True)),
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_merchants_hst_normalized ON merchants "
        "((regexp_replace(hst_number, '\\D', '', 'g'))) "
        "WHERE deleted_at IS NULL AND hst_number IS NOT NULL AND regexp_replace(hst_number, '\\D', '', 'g') <> ''"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_merchants_hst_normalized")
    op.drop_table("merchant_merges")
