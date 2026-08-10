"""M-26: merchant_users unique (clerk_user_id, merchant_id) for multi-seat.

Revision ID: g7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop global unique on clerk_user_id (name varies by initial schema).
    bind = op.get_bind()
    insp = sa.inspect(bind)
    for ix in insp.get_indexes("merchant_users"):
        cols = ix.get("column_names") or []
        if ix.get("unique") and cols == ["clerk_user_id"]:
            op.drop_index(ix["name"], table_name="merchant_users")
            break
    else:
        # Fallback common Alembic/SQLAlchemy names
        for name in (
            "ix_merchant_users_clerk_user_id",
            "merchant_users_clerk_user_id_key",
            "uq_merchant_users_clerk_user_id",
        ):
            try:
                op.drop_index(name, table_name="merchant_users")
                break
            except Exception:  # noqa: BLE001
                continue

    op.create_index(
        "ix_merchant_users_clerk_user_id",
        "merchant_users",
        ["clerk_user_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_merchant_users_clerk_merchant",
        "merchant_users",
        ["clerk_user_id", "merchant_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_merchant_users_clerk_merchant", "merchant_users", type_="unique")
    op.drop_index("ix_merchant_users_clerk_user_id", table_name="merchant_users")
    op.create_index(
        "ix_merchant_users_clerk_user_id",
        "merchant_users",
        ["clerk_user_id"],
        unique=True,
    )
