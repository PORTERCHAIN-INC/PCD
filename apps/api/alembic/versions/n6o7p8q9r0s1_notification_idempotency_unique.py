"""P2.5a — unique index on notification_records.search_tags idempotency_key."""

from __future__ import annotations

from alembic import op

revision = "n6o7p8q9r0s1"
down_revision = "m5n6o7p8q9r0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency key is already composite in value
    # (event|correlation|template|channel|recipient_type|recipient_id).
    # search_tags is JSON (not JSONB) — cast for operators / expression index.
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_records_idempotency_key
        ON notification_records (((search_tags::jsonb)->>'idempotency_key'))
        WHERE (search_tags::jsonb) ? 'idempotency_key'
          AND COALESCE((search_tags::jsonb)->>'idempotency_key', '') <> ''
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_notification_records_idempotency_key")
