"""Phase 4 — clerk_webhook_events idempotency table (additive).

Revision ID: x7y8z9a0b1c2
Revises: w6x7y8z9a0b1
Create Date: 2026-07-28
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "x7y8z9a0b1c2"
down_revision: Union[str, None] = "w6x7y8z9a0b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clerk_webhook_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("clerk_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processing"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_clerk_webhook_events_clerk_event_id"),
        "clerk_webhook_events",
        ["clerk_event_id"],
        unique=True,
    )
    op.create_index(op.f("ix_clerk_webhook_events_event_type"), "clerk_webhook_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_clerk_webhook_events_status"), "clerk_webhook_events", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_clerk_webhook_events_status"), table_name="clerk_webhook_events")
    op.drop_index(op.f("ix_clerk_webhook_events_event_type"), table_name="clerk_webhook_events")
    op.drop_index(op.f("ix_clerk_webhook_events_clerk_event_id"), table_name="clerk_webhook_events")
    op.drop_table("clerk_webhook_events")
