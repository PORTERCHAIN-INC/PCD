"""Dispatch Phase 2: fleet plans/routes, logistics partners, order legs; seed retention.

Seeds ``system_config['dispatch_retention']`` (GPS 30 days, POD 365 days) when missing.

Revision ID: dp0fleetplan2b3c
Revises: dj0joboffer1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "dp0fleetplan2b3c"
down_revision = "dj0joboffer1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dispatch_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("service_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("solver", sa.String(16), nullable=False, server_default="ortools"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("parent_id", sa.String(36), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_by", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("committed_by", sa.String(128), nullable=True),
        sa.Column("committed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_dispatch_plans_service_date", "dispatch_plans", ["service_date"])
    op.create_index("ix_dispatch_plans_status", "dispatch_plans", ["status"])
    op.create_index("ix_dispatch_plans_parent_id", "dispatch_plans", ["parent_id"])
    op.create_table(
        "dispatch_routes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("dispatch_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vehicle_id", sa.String(64), nullable=False),
        sa.Column("driver_id", sa.String(36), sa.ForeignKey("drivers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("vehicle_class", sa.String(32), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("fill_pct", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
    )
    op.create_index("ix_dispatch_routes_plan_id", "dispatch_routes", ["plan_id"])
    op.create_index("ix_dispatch_routes_driver_id", "dispatch_routes", ["driver_id"])
    op.create_table(
        "logistics_partners",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("fsa_coverage", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rate_per_kg_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_charge_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transit_days", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("cutoff_local", sa.String(5), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_logistics_partners_kind", "logistics_partners", ["kind"])
    op.create_index("ix_logistics_partners_active", "logistics_partners", ["active"])
    op.create_table(
        "order_legs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("order_id", sa.String(36), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("partner_id", sa.String(36), sa.ForeignKey("logistics_partners.id", ondelete="SET NULL"), nullable=True),
        sa.Column("from_label", sa.String(64), nullable=False, server_default=""),
        sa.Column("to_label", sa.String(64), nullable=False, server_default=""),
        sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
        sa.Column("est_cost_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_order_legs_order_id", "order_legs", ["order_id"])
    op.create_index("ix_order_legs_partner_id", "order_legs", ["partner_id"])
    op.create_index("ix_order_legs_status", "order_legs", ["status"])
    op.create_index("ix_order_legs_order_seq", "order_legs", ["order_id", "seq"])

    from porterchain_api.dispatch_engine.retention import STORAGE_KEY, default_retention

    conn = op.get_bind()
    if conn.execute(sa.text("SELECT 1 FROM system_config WHERE key = :k"), {"k": STORAGE_KEY}).first() is None:
        table = sa.table("system_config", sa.column("key", sa.String), sa.column("value", sa.JSON))
        op.bulk_insert(table, [{"key": STORAGE_KEY, "value": default_retention()}])


def downgrade() -> None:
    for name, table in (
        ("ix_order_legs_order_seq", "order_legs"), ("ix_order_legs_status", "order_legs"),
        ("ix_order_legs_partner_id", "order_legs"), ("ix_order_legs_order_id", "order_legs"),
    ):
        op.drop_index(name, table_name=table)
    op.drop_table("order_legs")
    op.drop_index("ix_logistics_partners_active", table_name="logistics_partners")
    op.drop_index("ix_logistics_partners_kind", table_name="logistics_partners")
    op.drop_table("logistics_partners")
    op.drop_index("ix_dispatch_routes_driver_id", table_name="dispatch_routes")
    op.drop_index("ix_dispatch_routes_plan_id", table_name="dispatch_routes")
    op.drop_table("dispatch_routes")
    op.drop_index("ix_dispatch_plans_parent_id", table_name="dispatch_plans")
    op.drop_index("ix_dispatch_plans_status", table_name="dispatch_plans")
    op.drop_index("ix_dispatch_plans_service_date", table_name="dispatch_plans")
    op.drop_table("dispatch_plans")
    # dispatch_retention seed row stays (settings data, not schema).
