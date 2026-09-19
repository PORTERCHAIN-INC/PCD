"""Order idempotency key for programmatic creates (Shopify/API retries)."""

from alembic import op
import sqlalchemy as sa

revision = "j2k3l4m5n6o7"
down_revision = "i9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("idempotency_key", sa.String(length=128), nullable=True))
    # Partial unique index: only rows that actually carry a key participate, so the
    # millions of portal/website orders with NULL keys stay unconstrained.
    op.create_index(
        "uq_orders_merchant_idempotency_key",
        "orders",
        ["merchant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_orders_merchant_idempotency_key", table_name="orders")
    op.drop_column("orders", "idempotency_key")
