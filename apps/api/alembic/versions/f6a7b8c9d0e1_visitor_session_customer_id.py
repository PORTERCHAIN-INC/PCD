"""Visitor session → customer FK (C-16).

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "visitor_sessions",
        sa.Column("customer_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_visitor_sessions_customer_id",
        "visitor_sessions",
        ["customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_visitor_sessions_customer_id", table_name="visitor_sessions")
    op.drop_column("visitor_sessions", "customer_id")
