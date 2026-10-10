"""Notification preferences: language + CASL marketing consent on user settings."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "nt2notifprefs1a2b"
down_revision = "nt1notifcenter1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("notification_user_settings", sa.Column("language", sa.String(length=8), nullable=True))
    op.add_column(
        "notification_user_settings", sa.Column("marketing_consent_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "notification_user_settings", sa.Column("marketing_consent_source", sa.String(length=64), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("notification_user_settings", "marketing_consent_source")
    op.drop_column("notification_user_settings", "marketing_consent_at")
    op.drop_column("notification_user_settings", "language")
