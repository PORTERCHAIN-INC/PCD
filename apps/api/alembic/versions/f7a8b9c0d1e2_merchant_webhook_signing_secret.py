"""Add encrypted_signing_secret to merchant_webhooks for outbound HMAC delivery.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "merchant_webhooks",
        sa.Column("encrypted_signing_secret", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("merchant_webhooks", "encrypted_signing_secret")
