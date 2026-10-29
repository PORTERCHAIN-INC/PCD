"""Drop the Clerk webhook idempotency table (Keycloak is the only identity provider).

Revision ID: kc7dropclerkwh0007
Revises: tr6taxreg0006
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "kc7dropclerkwh0007"
down_revision = "tr6taxreg0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS clerk_webhook_events")


def downgrade() -> None:
    op.create_table(
        "clerk_webhook_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("clerk_event_id", sa.String(length=128), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_clerk_webhook_events_clerk_event_id", "clerk_webhook_events", ["clerk_event_id"], unique=True)
