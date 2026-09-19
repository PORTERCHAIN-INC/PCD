"""drop route_center tables (Route Center removed — optimization is Fleetbase/VROOM)

Revision ID: a8b9c0d1e2f3
Revises: b2c3d4e5f6a7
Create Date: 2026-08-07
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("route_center_plans")
    op.drop_table("route_center_templates")


def downgrade() -> None:
    op.create_table(
        "route_center_templates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("template_type", sa.String(length=32), server_default="daily", nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("zone", sa.String(length=64), nullable=True),
        sa.Column("schedule", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("stops", postgresql.JSON(), server_default="[]", nullable=False),
        sa.Column("config", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "route_center_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="waiting", nullable=False),
        sa.Column("strategy", sa.String(length=32), server_default="balanced", nullable=False),
        sa.Column("zone", sa.String(length=64), nullable=True),
        sa.Column("order_ids", postgresql.JSON(), server_default="[]", nullable=False),
        sa.Column("stops", postgresql.JSON(), server_default="[]", nullable=False),
        sa.Column("driver_id", sa.String(length=36), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("simulation", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("recommendations", postgresql.JSON(), server_default="{}", nullable=False),
        sa.Column("fleetbase_run_id", sa.String(length=128), nullable=True),
        sa.Column("template_id", sa.String(length=36), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("approved_by", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
