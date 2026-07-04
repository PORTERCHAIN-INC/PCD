"""Order source/type and merchant billing cycle.

Revision ID: d5f6a7b8c9d0
Revises: c4e8f1a2b3d0
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5f6a7b8c9d0"
down_revision: Union[str, None] = "c4e8f1a2b3d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("order_source", sa.String(length=16), server_default="WEBSITE", nullable=False),
    )
    op.add_column(
        "orders",
        sa.Column("order_type", sa.String(length=16), server_default="INSTANT", nullable=False),
    )
    op.create_index("ix_orders_order_source", "orders", ["order_source"])
    op.create_index("ix_orders_order_type", "orders", ["order_type"])
    op.add_column(
        "merchants",
        sa.Column("billing_cycle", sa.String(length=16), server_default="MONTHLY", nullable=False),
    )
    # Classify existing merchant orders
    op.execute(
        "UPDATE orders SET order_source = 'MERCHANT' WHERE merchant_id IS NOT NULL AND order_source = 'WEBSITE'"
    )


def downgrade() -> None:
    op.drop_column("merchants", "billing_cycle")
    op.drop_index("ix_orders_order_type", table_name="orders")
    op.drop_index("ix_orders_order_source", table_name="orders")
    op.drop_column("orders", "order_type")
    op.drop_column("orders", "order_source")
