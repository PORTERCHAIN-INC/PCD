"""Drop dead analytics scaffold + unused packages.route_hint (one-SoT cleanup)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "q9r0s1t2u3v4"
down_revision = "p8q9r0s1t2u3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("packages", "route_hint")
    # Dead Phase-2 analytics scaffold — never ingested in production.
    op.execute("DROP TABLE IF EXISTS analytics_stop_legs")
    op.execute("DROP TABLE IF EXISTS analytics_events")


def downgrade() -> None:
    op.add_column("packages", sa.Column("route_hint", sa.Text(), nullable=True))
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_table(
        "analytics_stop_legs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("leg_index", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
    )
