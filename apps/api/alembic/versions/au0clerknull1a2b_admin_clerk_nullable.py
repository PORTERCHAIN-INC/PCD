"""Staff identity join is porterchain_user_id. clerk_user_id may be empty.

Revision ID: au0clerknull1a2b
Revises: dv0leadfk1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "au0clerknull1a2b"
down_revision = "dv0leadfk1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE admin_users AS a
            SET porterchain_user_id = p.id
            FROM porterchain_users AS p
            WHERE a.porterchain_user_id IS NULL
              AND p.email IS NOT NULL
              AND lower(p.email) = lower(a.email)
            """
        )
    )
    op.alter_column("admin_users", "clerk_user_id", existing_type=sa.String(length=128), nullable=True)


def downgrade() -> None:
    op.execute(sa.text("UPDATE admin_users SET clerk_user_id = 'staff:' || id WHERE clerk_user_id IS NULL"))
    op.alter_column("admin_users", "clerk_user_id", existing_type=sa.String(length=128), nullable=False)
