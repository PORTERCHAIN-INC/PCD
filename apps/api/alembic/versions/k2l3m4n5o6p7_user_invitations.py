"""user_invitations table

Revision ID: k2l3m4n5o6p7
Revises: j1k2l3m4n5o6
Create Date: 2026-07-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k2l3m4n5o6p7"
down_revision: Union[str, None] = "j1k2l3m4n5o6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_invitations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("user_type", sa.String(length=32), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("clerk_invitation_id", sa.String(length=128), nullable=True),
        sa.Column("clerk_user_id", sa.String(length=128), nullable=True),
        sa.Column("platform_user_id", sa.String(length=36), nullable=True),
        sa.Column("merchant_id", sa.String(length=36), nullable=True),
        sa.Column("invited_by", sa.String(length=36), nullable=True),
        sa.Column("redirect_url", sa.String(length=512), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_invitations_email"), "user_invitations", ["email"], unique=False)
    op.create_index(op.f("ix_user_invitations_user_type"), "user_invitations", ["user_type"], unique=False)
    op.create_index(op.f("ix_user_invitations_status"), "user_invitations", ["status"], unique=False)
    op.create_index(op.f("ix_user_invitations_clerk_user_id"), "user_invitations", ["clerk_user_id"], unique=False)
    op.create_index(op.f("ix_user_invitations_platform_user_id"), "user_invitations", ["platform_user_id"], unique=False)
    op.create_index(op.f("ix_user_invitations_merchant_id"), "user_invitations", ["merchant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_invitations_merchant_id"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_platform_user_id"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_clerk_user_id"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_status"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_user_type"), table_name="user_invitations")
    op.drop_index(op.f("ix_user_invitations_email"), table_name="user_invitations")
    op.drop_table("user_invitations")
