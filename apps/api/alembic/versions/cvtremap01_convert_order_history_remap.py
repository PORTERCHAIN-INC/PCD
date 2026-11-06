"""Remap order history for past customer↔merchant converts.

Revision ID: cvtremap01
Revises: shpsync01
Create Date: 2026-11-05

Data-only: for merchants created via Convert from customer, attach orphaned
orders (customer_id set, merchant_id NULL) to the merchant. For merchants
converted to retail customer, attach orders (merchant_id set, customer_id NULL)
to the converted customer. No schema change.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "cvtremap01"
down_revision: Union[str, None] = "shpsync01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # customer → merchant converts: profile.converted_from_customer_id
    op.execute(
        """
        UPDATE orders AS o
        SET merchant_id = m.id
        FROM merchants AS m
        WHERE m.profile IS NOT NULL
          AND (m.profile::jsonb ->> 'converted_from_customer_id') IS NOT NULL
          AND o.customer_id = (m.profile::jsonb ->> 'converted_from_customer_id')
          AND o.merchant_id IS NULL
        """
    )
    # merchant → customer converts: profile.converted_customer_id
    op.execute(
        """
        UPDATE orders AS o
        SET customer_id = (m.profile::jsonb ->> 'converted_customer_id')
        FROM merchants AS m
        WHERE m.profile IS NOT NULL
          AND (m.profile::jsonb ->> 'converted_customer_id') IS NOT NULL
          AND o.merchant_id = m.id
          AND o.customer_id IS NULL
        """
    )


def downgrade() -> None:
    # Irreversible data repair — no safe undo without a snapshot of prior FKs.
    pass
