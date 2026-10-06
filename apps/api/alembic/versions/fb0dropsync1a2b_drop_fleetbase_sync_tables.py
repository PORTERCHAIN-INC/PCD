"""Drop the unused Fleetbase sync queue tables.

Revision ID: fb0dropsync1a2b
Revises: pr0shopdsr1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "fb0dropsync1a2b"
down_revision = "pr0shopdsr1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fleetbase_sync_jobs_inflight_idempotency")
    op.execute("DROP INDEX IF EXISTS ix_fleetbase_sync_jobs_pending")
    op.execute("DROP TABLE IF EXISTS fleetbase_sync_jobs")
    op.execute("DROP TABLE IF EXISTS fleetbase_sync_audit")


def downgrade() -> None:
    op.create_table(
        "fleetbase_sync_audit",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("fleetbase_order_id", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "fleetbase_sync_jobs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("order_id", sa.String(length=36), nullable=True),
        sa.Column("fleetbase_order_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
