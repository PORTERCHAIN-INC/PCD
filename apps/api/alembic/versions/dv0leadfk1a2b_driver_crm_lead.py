"""Link a pending driver back to the CRM lead that provisioned it.

Revision ID: dv0leadfk1a2b
Revises: cq0uoteid1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "dv0leadfk1a2b"
down_revision = "cq0uoteid1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("drivers", sa.Column("crm_lead_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_drivers_crm_lead_id",
        "drivers",
        "crm_leads",
        ["crm_lead_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "uq_drivers_crm_lead_id",
        "drivers",
        ["crm_lead_id"],
        unique=True,
        postgresql_where=sa.text("crm_lead_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_drivers_crm_lead_id", table_name="drivers")
    op.drop_constraint("fk_drivers_crm_lead_id", "drivers", type_="foreignkey")
    op.drop_column("drivers", "crm_lead_id")
