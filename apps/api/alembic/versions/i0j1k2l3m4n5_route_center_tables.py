"""Route Center plans and templates.

Revision ID: i0j1k2l3m4n5
Revises: h9i0j1k2l3m4
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i0j1k2l3m4n5"
down_revision: Union[str, None] = "h9i0j1k2l3m4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "route_center_plans",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="waiting"),
        sa.Column("strategy", sa.String(length=32), nullable=False, server_default="balanced"),
        sa.Column("zone", sa.String(length=64), nullable=True),
        sa.Column("order_ids", sa.JSON(), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column("driver_id", sa.String(length=36), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("simulation", sa.JSON(), nullable=False),
        sa.Column("recommendations", sa.JSON(), nullable=False),
        sa.Column("fleetbase_run_id", sa.String(length=128), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_center_plans_status", "route_center_plans", ["status"])
    op.create_index("ix_route_center_plans_zone", "route_center_plans", ["zone"])
    op.create_index("ix_route_center_plans_driver_id", "route_center_plans", ["driver_id"])
    op.create_index("ix_route_center_plans_vehicle_id", "route_center_plans", ["vehicle_id"])
    op.create_index("ix_route_center_plans_template_id", "route_center_plans", ["template_id"])

    op.create_table(
        "route_center_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("template_type", sa.String(length=32), nullable=False, server_default="daily"),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("zone", sa.String(length=64), nullable=True),
        sa.Column("schedule", sa.JSON(), nullable=False),
        sa.Column("stops", sa.JSON(), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_route_center_templates_template_type", "route_center_templates", ["template_type"])
    op.create_index("ix_route_center_templates_merchant_id", "route_center_templates", ["merchant_id"])


def downgrade() -> None:
    op.drop_index("ix_route_center_templates_merchant_id", table_name="route_center_templates")
    op.drop_index("ix_route_center_templates_template_type", table_name="route_center_templates")
    op.drop_table("route_center_templates")
    op.drop_index("ix_route_center_plans_template_id", table_name="route_center_plans")
    op.drop_index("ix_route_center_plans_vehicle_id", table_name="route_center_plans")
    op.drop_index("ix_route_center_plans_driver_id", table_name="route_center_plans")
    op.drop_index("ix_route_center_plans_zone", table_name="route_center_plans")
    op.drop_index("ix_route_center_plans_status", table_name="route_center_plans")
    op.drop_table("route_center_plans")
