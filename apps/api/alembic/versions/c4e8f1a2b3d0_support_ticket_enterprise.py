"""Support ticket enterprise fields.

Revision ID: c4e8f1a2b3d0
Revises: bd830e39ef4e
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8f1a2b3d0"
down_revision: Union[str, None] = "bd830e39ef4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "support_tickets",
        sa.Column("category", sa.String(length=64), server_default="general_inquiry", nullable=False),
    )
    op.add_column(
        "support_tickets",
        sa.Column("ticket_data", sa.JSON(), server_default="{}", nullable=False),
    )
    op.create_index("ix_support_tickets_category", "support_tickets", ["category"])


def downgrade() -> None:
    op.drop_index("ix_support_tickets_category", table_name="support_tickets")
    op.drop_column("support_tickets", "ticket_data")
    op.drop_column("support_tickets", "category")
