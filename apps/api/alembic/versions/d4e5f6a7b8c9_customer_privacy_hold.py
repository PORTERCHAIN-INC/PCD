"""customers.privacy_status — GDPR DSR hold (Wave 1 C-19).

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-08
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("privacy_status", sa.String(length=32), nullable=True))
    op.add_column("customers", sa.Column("privacy_hold_reference", sa.String(length=64), nullable=True))
    op.add_column("customers", sa.Column("privacy_hold_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_customers_privacy_status", "customers", ["privacy_status"])


def downgrade() -> None:
    op.drop_index("ix_customers_privacy_status", table_name="customers")
    op.drop_column("customers", "privacy_hold_at")
    op.drop_column("customers", "privacy_hold_reference")
    op.drop_column("customers", "privacy_status")
