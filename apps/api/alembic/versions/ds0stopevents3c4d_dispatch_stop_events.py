"""Dispatch Round 3: driver stop check-ins (GPS) + partner ops contact email.

Revision ID: ds0stopevents3c4d
Revises: dp0fleetplan2b3c
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ds0stopevents3c4d"
down_revision = "dp0fleetplan2b3c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_stop_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("route_id", sa.String(36), sa.ForeignKey("dispatch_routes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("stop_key", sa.String(96), nullable=False),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("driver_id", sa.String(36), sa.ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event", sa.String(16), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("accuracy_m", sa.Float(), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    for col in ("route_id", "stop_key", "order_id", "driver_id", "event", "at"):
        op.create_index(f"ix_dispatch_stop_events_{col}", "dispatch_stop_events", [col])
    op.create_index("ix_dispatch_stop_events_route_key", "dispatch_stop_events", ["route_id", "stop_key"])
    op.add_column("logistics_partners", sa.Column("contact_email", sa.String(255), nullable=True))
    # Legacy leg statuses → booking workflow names.
    op.execute("UPDATE order_legs SET status = 'requested' WHERE status = 'booked'")
    op.execute("UPDATE order_legs SET status = 'picked_up' WHERE status = 'in_transit'")
    op.execute("UPDATE order_legs SET status = 'delivered' WHERE status = 'done'")


def downgrade() -> None:
    op.execute("UPDATE order_legs SET status = 'booked' WHERE status IN ('requested', 'accepted')")
    op.execute("UPDATE order_legs SET status = 'in_transit' WHERE status = 'picked_up'")
    op.execute("UPDATE order_legs SET status = 'done' WHERE status = 'delivered'")
    op.drop_column("logistics_partners", "contact_email")
    op.drop_index("ix_dispatch_stop_events_route_key", table_name="dispatch_stop_events")
    for col in ("at", "event", "driver_id", "order_id", "stop_key", "route_id"):
        op.drop_index(f"ix_dispatch_stop_events_{col}", table_name="dispatch_stop_events")
    op.drop_table("dispatch_stop_events")
