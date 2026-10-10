"""Notification idempotency key as an indexed column, plus a dedupe/rate-limit family column.

Replaces the JSON expression index on search_tags->>'idempotency_key' (n6o7p8q9r0s1)
with a plain unique partial index on a real column. Backfills from search_tags.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "nt0emailnotif1a2b"
down_revision = "lp0leadpipe1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_records", sa.Column("idempotency_key", sa.String(length=255), nullable=True))
    op.add_column("notification_records", sa.Column("dedupe_family", sa.String(length=160), nullable=True))
    op.execute(
        """
        UPDATE notification_records
        SET idempotency_key = LEFT((search_tags::jsonb)->>'idempotency_key', 255)
        WHERE (search_tags::jsonb) ? 'idempotency_key'
          AND COALESCE((search_tags::jsonb)->>'idempotency_key', '') <> ''
        """
    )
    op.create_index(
        "uq_notification_records_idem_col",
        "notification_records",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index("ix_notification_records_dedupe_family", "notification_records", ["dedupe_family"])
    op.execute("DROP INDEX IF EXISTS uq_notification_records_idempotency_key")


def downgrade() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_notification_records_idempotency_key
        ON notification_records (((search_tags::jsonb)->>'idempotency_key'))
        WHERE (search_tags::jsonb) ? 'idempotency_key'
          AND COALESCE((search_tags::jsonb)->>'idempotency_key', '') <> ''
        """
    )
    op.drop_index("ix_notification_records_dedupe_family", table_name="notification_records")
    op.drop_index("uq_notification_records_idem_col", table_name="notification_records")
    op.drop_column("notification_records", "dedupe_family")
    op.drop_column("notification_records", "idempotency_key")
