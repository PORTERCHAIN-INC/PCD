"""C-18: customers.stripe_customer_id for wallet / Admin 360.

Revision ID: h8c9d0e1f2a3
Revises: g7b8c9d0e1f2
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, None] = "g7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("stripe_customer_id", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_customers_stripe_customer_id",
        "customers",
        ["stripe_customer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_customers_stripe_customer_id", table_name="customers")
    op.drop_column("customers", "stripe_customer_id")
