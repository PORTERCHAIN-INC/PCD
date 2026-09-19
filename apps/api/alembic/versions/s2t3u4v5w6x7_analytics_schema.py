"""Analytics warehouse tables — Phase 2 scaffold (§4.1.2)."""

from alembic import op
import sqlalchemy as sa

revision = "s2t3u4v5w6x7"
down_revision = "r1s2t3u4v5w6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("aggregate_id", sa.String(length=36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_events_event_type", "analytics_events", ["event_type"])
    op.create_index("ix_analytics_events_aggregate_id", "analytics_events", ["aggregate_id"])
    op.create_index("ix_analytics_events_occurred_at", "analytics_events", ["occurred_at"])

    op.create_table(
        "analytics_stop_legs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=False),
        sa.Column("leg_index", sa.Integer(), nullable=False),
        sa.Column("lat", sa.Float(), nullable=False),
        sa.Column("lng", sa.Float(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_stop_legs_order_id", "analytics_stop_legs", ["order_id"])
    op.create_index("ix_analytics_stop_legs_recorded_at", "analytics_stop_legs", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_analytics_stop_legs_recorded_at", table_name="analytics_stop_legs")
    op.drop_index("ix_analytics_stop_legs_order_id", table_name="analytics_stop_legs")
    op.drop_table("analytics_stop_legs")
    op.drop_index("ix_analytics_events_occurred_at", table_name="analytics_events")
    op.drop_index("ix_analytics_events_aggregate_id", table_name="analytics_events")
    op.drop_index("ix_analytics_events_event_type", table_name="analytics_events")
    op.drop_table("analytics_events")
