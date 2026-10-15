"""Widen correlation_id on domain_events and order_events to 128.

Composite ids such as "<uuid>:<hex>" (45 chars) overflowed VARCHAR(36) and made
notification.queued inserts fail. Widening a VARCHAR in Postgres is metadata-only
(no table rewrite) and loses no data.
"""

import sqlalchemy as sa
from alembic import op

revision = "cw0corrwide0001"
down_revision = "ba0attach0001"
branch_labels = None
depends_on = None

_TABLES = ("domain_events", "order_events")


def upgrade() -> None:
    for table in _TABLES:
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "correlation_id",
                existing_type=sa.String(36),
                type_=sa.String(128),
                existing_nullable=True,
            )


def downgrade() -> None:
    for table in _TABLES:
        op.execute(f"UPDATE {table} SET correlation_id = LEFT(correlation_id, 36) WHERE LENGTH(correlation_id) > 36")
        with op.batch_alter_table(table) as batch:
            batch.alter_column(
                "correlation_id",
                existing_type=sa.String(128),
                type_=sa.String(36),
                existing_nullable=True,
            )
