"""Add AdminUser.phone for staff SMS push fallback."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a9b0c1d2e3f4"
down_revision = "z8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("admin_users", sa.Column("phone", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("admin_users", "phone")
