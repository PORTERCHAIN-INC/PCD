"""CrmSuppression — global hashed DNC for CASL / GDPR object.

Revision ID: cs0suppress1a2b
Revises: ld0360vis1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "cs0suppress1a2b"
down_revision = "ld0360vis1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_suppressions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("hash_kind", sa.String(length=16), nullable=False),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="unsubscribe"),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("hash_kind", "value_hash", name="uq_crm_suppressions_kind_hash"),
    )
    op.create_index("ix_crm_suppressions_hash_kind", "crm_suppressions", ["hash_kind"])
    op.create_index("ix_crm_suppressions_value_hash", "crm_suppressions", ["value_hash"])
    op.create_index("ix_crm_suppressions_lead_id", "crm_suppressions", ["lead_id"])


def downgrade() -> None:
    op.drop_index("ix_crm_suppressions_lead_id", table_name="crm_suppressions")
    op.drop_index("ix_crm_suppressions_value_hash", table_name="crm_suppressions")
    op.drop_index("ix_crm_suppressions_hash_kind", table_name="crm_suppressions")
    op.drop_table("crm_suppressions")
