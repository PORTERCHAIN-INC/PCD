"""Enforce one order per quote for retail checkout idempotency."""

from alembic import op

revision = "n2o3p4q5r6s7"
down_revision = "m1n2o3p4q5r6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_orders_quote_id",
        "orders",
        ["quote_id"],
        unique=True,
        postgresql_where="quote_id IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_index("uq_orders_quote_id", table_name="orders")
