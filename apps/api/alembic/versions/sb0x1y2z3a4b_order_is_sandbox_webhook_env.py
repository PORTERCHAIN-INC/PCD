"""Order.is_sandbox + webhook environment + env-scoped idempotency."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "sb0x1y2z3a4b"
down_revision = "x6y7z8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_orders_is_sandbox", "orders", ["is_sandbox"])

    # Backfill from legacy compliance_metadata.sandbox JSON flag.
    op.execute(
        sa.text(
            """
            UPDATE orders
            SET is_sandbox = true
            WHERE compliance_metadata IS NOT NULL
              AND (compliance_metadata->>'sandbox') IN ('true', 'True', '1')
            """
        )
    )

    op.drop_index("uq_orders_merchant_idempotency_key", table_name="orders")
    op.create_index(
        "uq_orders_merchant_idempotency_sandbox",
        "orders",
        ["merchant_id", "idempotency_key", "is_sandbox"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )

    op.add_column(
        "merchant_webhooks",
        sa.Column("environment", sa.String(length=16), nullable=False, server_default="production"),
    )
    op.create_index("ix_merchant_webhooks_environment", "merchant_webhooks", ["environment"])


def downgrade() -> None:
    op.drop_index("ix_merchant_webhooks_environment", table_name="merchant_webhooks")
    op.drop_column("merchant_webhooks", "environment")

    op.drop_index("uq_orders_merchant_idempotency_sandbox", table_name="orders")
    op.create_index(
        "uq_orders_merchant_idempotency_key",
        "orders",
        ["merchant_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_index("ix_orders_is_sandbox", table_name="orders")
    op.drop_column("orders", "is_sandbox")
