"""Unique quote identity on CRM leads for the booking mirror.

Revision ID: cq0uoteid1a2b
Revises: rf0undkey1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "cq0uoteid1a2b"
down_revision = "rf0undkey1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crm_leads", sa.Column("quote_id", sa.String(length=36), nullable=True))
    op.create_index(
        "uq_crm_leads_quote_id",
        "crm_leads",
        ["quote_id"],
        unique=True,
        postgresql_where=sa.text("quote_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_crm_leads_quote_id", table_name="crm_leads")
    op.drop_column("crm_leads", "quote_id")
