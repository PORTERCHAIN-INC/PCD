"""Dispatch Round 4: learned stop times, idempotent driver check-ins, applied exception fixes.

Revision ID: r4planinputs7a8b
Revises: fx0retirefleet5e6f
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "r4planinputs7a8b"
down_revision = "fx0retirefleet5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_stop_times",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scope", sa.String(8), nullable=False),  # fsa | place
        sa.Column("scope_key", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(8), nullable=False),  # pickup | drop
        sa.Column("median_s", sa.Integer(), nullable=False),
        sa.Column("samples", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("scope", "scope_key", "kind", name="uq_dispatch_stop_times_key"),
    )
    op.add_column("dispatch_stop_events", sa.Column("client_id", sa.String(64), nullable=True))
    op.create_index("uq_dispatch_stop_events_client_id", "dispatch_stop_events", ["client_id"], unique=True)
    op.create_table(
        "dispatch_fix_actions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("item_id", sa.String(96), nullable=False, index=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("params", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("approved_by", sa.String(128), nullable=False),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("dispatch_fix_actions")
    op.drop_index("uq_dispatch_stop_events_client_id", table_name="dispatch_stop_events")
    op.drop_column("dispatch_stop_events", "client_id")
    op.drop_table("dispatch_stop_times")
