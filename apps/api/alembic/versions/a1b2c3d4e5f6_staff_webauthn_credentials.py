"""Staff WebAuthn / passkey credentials table."""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "z9a0b1c2d3e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_webauthn_credentials",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("admin_user_id", sa.String(length=36), nullable=False),
        sa.Column("credential_id", sa.String(length=512), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("sign_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("device_label", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_staff_webauthn_credentials_admin_user_id", "staff_webauthn_credentials", ["admin_user_id"])
    op.create_index(
        "ix_staff_webauthn_credentials_credential_id",
        "staff_webauthn_credentials",
        ["credential_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_staff_webauthn_credentials_credential_id", table_name="staff_webauthn_credentials")
    op.drop_index("ix_staff_webauthn_credentials_admin_user_id", table_name="staff_webauthn_credentials")
    op.drop_table("staff_webauthn_credentials")
