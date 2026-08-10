"""notification_user_settings — quiet hours (Phase 3).

Revision ID: c3d4e5f6a7b8
Revises: a8b9c0d1e2f3
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3d4e5f6a7b8"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "notification_user_settings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_role", sa.String(length=32), nullable=False, index=True),
        sa.Column("user_id", sa.String(length=36), nullable=False, index=True),
        sa.Column("quiet_hours_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("quiet_start_hour", sa.Integer(), nullable=False, server_default="22"),
        sa.Column("quiet_end_hour", sa.Integer(), nullable=False, server_default="7"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="America/Toronto"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_role", "user_id", name="uq_notification_user_settings_role_user"),
    )


def downgrade() -> None:
    op.drop_table("notification_user_settings")
