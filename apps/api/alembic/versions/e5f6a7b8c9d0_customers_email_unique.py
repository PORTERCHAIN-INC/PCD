"""Unique lower(email) on customers — Wave 2 C-14.

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Keep the oldest row per email; clear email on newer duplicates so the unique
    # index can apply (merge logic in CustomerService.upsert rebinds on next login).
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY lower(email)
                       ORDER BY created_at ASC NULLS LAST, id ASC
                   ) AS rn
            FROM customers
            WHERE email IS NOT NULL AND btrim(email) <> ''
        )
        UPDATE customers c
        SET email = c.email || '+dup.' || substr(c.id, 1, 8)
        FROM ranked r
        WHERE c.id = r.id AND r.rn > 1
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_customers_email_lower ON customers (lower(email))"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_customers_email_lower")
