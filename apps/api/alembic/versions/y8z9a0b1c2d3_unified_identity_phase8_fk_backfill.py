"""Phase 8 — additive porterchain_user_id on profile tables (keep clerk_user_id).

Revision ID: y8z9a0b1c2d3
Revises: x7y8z9a0b1c2
Create Date: 2026-07-28

Non-destructive: nullable FK columns only; no drops; no data rewrite in migration.
Backfill is a separate dry-run-first CLI.
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "y8z9a0b1c2d3"
down_revision: Union[str, None] = "x7y8z9a0b1c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = (
    "admin_users",
    "merchant_users",
    "customers",
    "drivers",
    "user_invitations",
)


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(
            table,
            sa.Column("porterchain_user_id", sa.String(length=36), nullable=True),
        )
        op.create_index(
            f"ix_{table}_porterchain_user_id",
            table,
            ["porterchain_user_id"],
            unique=False,
        )
        op.create_foreign_key(
            f"fk_{table}_porterchain_user_id",
            table,
            "porterchain_users",
            ["porterchain_user_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_constraint(f"fk_{table}_porterchain_user_id", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_porterchain_user_id", table_name=table)
        op.drop_column(table, "porterchain_user_id")
