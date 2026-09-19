"""Driver shift and activity tables.

Revision ID: h9i0j1k2l3m4
Revises: g8h9i0j1k2l3
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h9i0j1k2l3m4"
down_revision: Union[str, None] = "g8h9i0j1k2l3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "driver_shifts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("driver_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("break_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("route_id", sa.String(length=128), nullable=True),
        sa.Column("mileage_km", sa.Float(), nullable=False, server_default="0"),
        sa.Column("break_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("meta", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_driver_shifts_driver_id", "driver_shifts", ["driver_id"])
    op.create_index("ix_driver_shifts_status", "driver_shifts", ["status"])
    op.create_index("ix_driver_shifts_vehicle_id", "driver_shifts", ["vehicle_id"])

    op.create_table(
        "driver_shift_activities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("shift_id", sa.String(length=36), nullable=True),
        sa.Column("driver_id", sa.String(length=36), nullable=False),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["driver_id"], ["drivers.id"]),
        sa.ForeignKeyConstraint(["shift_id"], ["driver_shifts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_driver_shift_activities_driver_id", "driver_shift_activities", ["driver_id"])
    op.create_index("ix_driver_shift_activities_shift_id", "driver_shift_activities", ["shift_id"])
    op.create_index("ix_driver_shift_activities_activity_type", "driver_shift_activities", ["activity_type"])


def downgrade() -> None:
    op.drop_index("ix_driver_shift_activities_activity_type", table_name="driver_shift_activities")
    op.drop_index("ix_driver_shift_activities_shift_id", table_name="driver_shift_activities")
    op.drop_index("ix_driver_shift_activities_driver_id", table_name="driver_shift_activities")
    op.drop_table("driver_shift_activities")
    op.drop_index("ix_driver_shifts_vehicle_id", table_name="driver_shifts")
    op.drop_index("ix_driver_shifts_status", table_name="driver_shifts")
    op.drop_index("ix_driver_shifts_driver_id", table_name="driver_shifts")
    op.drop_table("driver_shifts")
