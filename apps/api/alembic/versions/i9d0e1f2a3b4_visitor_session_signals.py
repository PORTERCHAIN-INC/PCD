"""Visitor session signals + intent_score (visitor intelligence).

Revision ID: i9d0e1f2a3b4
Revises: h8c9d0e1f2a3
Create Date: 2026-08-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "i9d0e1f2a3b4"
down_revision: Union[str, None] = "h8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("visitor_sessions", sa.Column("signals", sa.JSON(), nullable=True))
    op.add_column(
        "visitor_sessions",
        sa.Column("touch_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "visitor_sessions",
        sa.Column("intent_score", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("visitor_sessions", "intent_score")
    op.drop_column("visitor_sessions", "touch_count")
    op.drop_column("visitor_sessions", "signals")
