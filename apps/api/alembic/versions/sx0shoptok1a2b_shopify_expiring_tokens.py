"""Shopify expiring offline tokens: expiry, refresh token, token status.

Shopify rejects non-expiring offline tokens for this public app. Each shop now keeps
the expiring access token's expiry, an encrypted refresh token and its expiry, and a
token status (expiring / custom_app / token_reauth_required; NULL = legacy token).

Revision ID: sx0shoptok1a2b
Revises: fb0dropsync1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "sx0shoptok1a2b"
down_revision = "fb0dropsync1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "shopify_shops",
        sa.Column("access_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("shopify_shops", sa.Column("encrypted_refresh_token", sa.Text(), nullable=True))
    op.add_column(
        "shopify_shops",
        sa.Column("refresh_token_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("shopify_shops", sa.Column("token_status", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("shopify_shops", "token_status")
    op.drop_column("shopify_shops", "refresh_token_expires_at")
    op.drop_column("shopify_shops", "encrypted_refresh_token")
    op.drop_column("shopify_shops", "access_token_expires_at")
