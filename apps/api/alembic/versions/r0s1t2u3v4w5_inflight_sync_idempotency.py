"""Partial unique index: one in-flight Fleetbase sync job per idempotency_key.

GPS tracking uses tracking:{driver_id}. Without this constraint concurrent
pings INSERT duplicate pending rows (P0-3). done/dead rows keep the same key,
so uniqueness is pending|retrying only.
"""

from __future__ import annotations

from alembic import op

revision = "r0s1t2u3v4w5"
down_revision = "q9r0s1t2u3v4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY idempotency_key
                       ORDER BY updated_at DESC NULLS LAST, created_at DESC
                   ) AS rn
            FROM fleetbase_sync_jobs
            WHERE status IN ('pending', 'retrying')
              AND idempotency_key IS NOT NULL
        )
        UPDATE fleetbase_sync_jobs AS j
        SET status = 'done',
            last_error = 'dup_inflight_gps',
            updated_at = NOW()
        FROM ranked
        WHERE j.id = ranked.id
          AND ranked.rn > 1
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fleetbase_sync_jobs_inflight_idempotency
        ON fleetbase_sync_jobs (idempotency_key)
        WHERE status IN ('pending', 'retrying')
          AND idempotency_key IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fleetbase_sync_jobs_inflight_idempotency")
