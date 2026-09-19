"""Widen domain_events.aggregate_id for Stripe/external webhook ids.

Stripe event ids (evt_…) routinely exceed 36 chars; WEBHOOK_RECEIVED uses the
raw stripe event id as aggregate_id. Matching stripe_webhook_events.stripe_event_id
at String(255).
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "c1d2e3f4a5b6"
down_revision = "b0c1d2e3f4a5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "domain_events",
        "aggregate_id",
        existing_type=sa.String(length=36),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "domain_events",
        "aggregate_id",
        existing_type=sa.String(length=255),
        type_=sa.String(length=36),
        existing_nullable=False,
    )
