"""Shopify carrier, fulfillment service, and webhook-id columns.

Revision ID: sh2gqlids3c4d
Revises: bg0schedauth1a2b, mg0crmsup1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "sh2gqlids3c4d"
down_revision = ("bg0schedauth1a2b", "mg0crmsup1a2b")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_shops",
        sa.Column("carrier_service_gid", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "shopify_shops",
        sa.Column("fulfillment_service_gid", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "shopify_shops",
        sa.Column("location_gid", sa.String(length=128), nullable=True),
    )
    op.add_column("shopify_shops", sa.Column("seen_webhook_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("shopify_shops", "seen_webhook_ids")
    op.drop_column("shopify_shops", "location_gid")
    op.drop_column("shopify_shops", "fulfillment_service_gid")
    op.drop_column("shopify_shops", "carrier_service_gid")
