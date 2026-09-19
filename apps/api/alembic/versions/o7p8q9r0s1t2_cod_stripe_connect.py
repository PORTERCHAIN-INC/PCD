"""COD + Stripe Connect columns on orders and merchants."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "o7p8q9r0s1t2"
down_revision = "n6o7p8q9r0s1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("cod_amount_cents", sa.Integer(), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("cod_status", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("cod_stripe_session_id", sa.String(length=255), nullable=True),
    )
    op.create_index("ix_orders_cod_status", "orders", ["cod_status"])

    op.add_column(
        "merchants",
        sa.Column("stripe_connect_account_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "merchants",
        sa.Column("cod_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.drop_column("merchants", "cod_enabled")
    op.drop_column("merchants", "stripe_connect_account_id")
    op.drop_index("ix_orders_cod_status", table_name="orders")
    op.drop_column("orders", "cod_stripe_session_id")
    op.drop_column("orders", "cod_status")
    op.drop_column("orders", "cod_amount_cents")
