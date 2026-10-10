"""Dispatch job offers (expire after TTL, cascade to next driver); seed dispatch_fleet.

Seeds ``system_config['dispatch_fleet']`` (vehicle capacity table, $27/h,
85% max fill, 180 s offer TTL) only when missing — an existing row is kept.

Revision ID: dj0joboffer1a2b
Revises: ma0merchops1a2b (integration chain)
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "dj0joboffer1a2b"
down_revision = "ma0merchops1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_job_offers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("driver_id", sa.String(36), sa.ForeignKey("drivers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("rank", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("offered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("offered_by", sa.String(128), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_index("ix_dispatch_job_offers_order_id", "dispatch_job_offers", ["order_id"])
    op.create_index("ix_dispatch_job_offers_driver_id", "dispatch_job_offers", ["driver_id"])
    op.create_index("ix_dispatch_job_offers_status", "dispatch_job_offers", ["status"])
    op.create_index("ix_dispatch_job_offers_expires_at", "dispatch_job_offers", ["expires_at"])
    op.create_index("ix_dispatch_job_offers_order_status", "dispatch_job_offers", ["order_id", "status"])

    from porterchain_api.dispatch_engine.fleet_capacity import STORAGE_KEY, default_fleet

    conn = op.get_bind()
    exists = conn.execute(sa.text("SELECT 1 FROM system_config WHERE key = :k"), {"k": STORAGE_KEY}).first()
    if exists is None:
        table = sa.table("system_config", sa.column("key", sa.String), sa.column("value", sa.JSON))
        op.bulk_insert(table, [{"key": STORAGE_KEY, "value": default_fleet()}])


def downgrade() -> None:
    op.drop_index("ix_dispatch_job_offers_order_status", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_expires_at", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_status", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_driver_id", table_name="dispatch_job_offers")
    op.drop_index("ix_dispatch_job_offers_order_id", table_name="dispatch_job_offers")
    op.drop_table("dispatch_job_offers")
    # dispatch_fleet seed row is left in place (settings data, not schema).
