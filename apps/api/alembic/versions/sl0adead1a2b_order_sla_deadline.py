"""Persist order SLA promise deadline for bounded control-tower counts.

Revision ID: sl0adead1a2b
Revises: sh1polreg2b3c
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "sl0adead1a2b"
down_revision = "sh1polreg2b3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("sla_deadline_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_orders_sla_deadline_at", "orders", ["sla_deadline_at"])


def downgrade() -> None:
    op.drop_index("ix_orders_sla_deadline_at", table_name="orders")
    op.drop_column("orders", "sla_deadline_at")
