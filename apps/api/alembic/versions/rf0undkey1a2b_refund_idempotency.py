"""Unique refund claim key on the billing ledger.

Revision ID: rf0undkey1a2b
Revises: sl0adead1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "rf0undkey1a2b"
down_revision = "sl0adead1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "billing_ledger_entries",
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "uq_billing_ledger_idempotency_key",
        "billing_ledger_entries",
        ["idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_billing_ledger_idempotency_key", table_name="billing_ledger_entries")
    op.drop_column("billing_ledger_entries", "idempotency_key")
