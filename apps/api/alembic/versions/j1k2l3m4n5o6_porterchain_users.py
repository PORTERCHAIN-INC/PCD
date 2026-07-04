"""porterchain_users — canonical Clerk identity registry

Revision ID: j1k2l3m4n5o6
Revises: i0j1k2l3m4n5
Create Date: 2026-07-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "j1k2l3m4n5o6"
down_revision: Union[str, None] = "i0j1k2l3m4n5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "porterchain_users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("profile", sa.JSON(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_porterchain_users_clerk_user_id"), "porterchain_users", ["clerk_user_id"], unique=True)
    op.create_index(op.f("ix_porterchain_users_email"), "porterchain_users", ["email"], unique=False)
    op.create_index(op.f("ix_porterchain_users_role"), "porterchain_users", ["role"], unique=False)
    op.create_index(op.f("ix_porterchain_users_status"), "porterchain_users", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_porterchain_users_status"), table_name="porterchain_users")
    op.drop_index(op.f("ix_porterchain_users_role"), table_name="porterchain_users")
    op.drop_index(op.f("ix_porterchain_users_email"), table_name="porterchain_users")
    op.drop_index(op.f("ix_porterchain_users_clerk_user_id"), table_name="porterchain_users")
    op.drop_table("porterchain_users")
