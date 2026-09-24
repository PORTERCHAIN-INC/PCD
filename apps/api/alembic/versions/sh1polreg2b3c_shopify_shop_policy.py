"""Shopify shop booking policy columns + auto_dispatch default false for new rows.

Revision ID: sh1polreg2b3c
Revises: sh0pingress1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "sh1polreg2b3c"
down_revision = "sh0pingress1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_shops",
        sa.Column("default_vehicle_class", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "shopify_shops",
        sa.Column("default_package_type", sa.String(length=64), nullable=True),
    )
    # New shops default to hold-at-BOOKED; existing rows keep current values.
    op.alter_column(
        "shopify_shops",
        "auto_dispatch",
        server_default=sa.false(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "shopify_shops",
        "auto_dispatch",
        server_default=sa.true(),
        existing_type=sa.Boolean(),
        existing_nullable=False,
    )
    op.drop_column("shopify_shops", "default_package_type")
    op.drop_column("shopify_shops", "default_vehicle_class")
