"""Merchants pay invoices by Interac e-Transfer only: drop merchants.stripe_enabled.

Revision ID: m1i2n3t4e5r6
Revises: r4planinputs7a8b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "m1i2n3t4e5r6"
down_revision = "r4planinputs7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("merchants", "stripe_enabled")


def downgrade() -> None:
    op.add_column(
        "merchants",
        sa.Column("stripe_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
