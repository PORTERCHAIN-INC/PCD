"""Lead pipeline: New / Replied / Quoted / Won / Lost + lost reason.

Revision ID: lp0leadpipe1a2b
Revises: li0leadinbox1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "lp0leadpipe1a2b"
down_revision = "li0leadinbox1a2b"
branch_labels = None
depends_on = None

_FORWARD = {
    "contacted": "replied",
    "qualified": "replied",
    "nurturing": "replied",
    "converted": "won",
    "unqualified": "lost",
}
# Used only for rows created after the upgrade (no legacy_status to restore).
_BACKWARD = {"replied": "contacted", "quoted": "qualified", "won": "converted", "lost": "unqualified"}


def upgrade() -> None:
    op.add_column("crm_leads", sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_leads", sa.Column("won_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_leads", sa.Column("lost_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_leads", sa.Column("lost_reason", sa.String(32), nullable=True))
    op.add_column("crm_leads", sa.Column("legacy_status", sa.String(32), nullable=True))
    op.create_index("ix_crm_leads_lost_reason", "crm_leads", ["lost_reason"])
    for old, new in _FORWARD.items():
        op.execute(
            sa.text(
                "UPDATE crm_leads SET legacy_status = status, status = :new, "
                "won_at = CASE WHEN :new = 'won' THEN COALESCE(updated_at, created_at) END, "
                "lost_at = CASE WHEN :new = 'lost' THEN COALESCE(updated_at, created_at) END "
                "WHERE status = :old"
            ).bindparams(old=old, new=new)
        )


def downgrade() -> None:
    op.execute(
        "UPDATE crm_leads SET status = legacy_status "
        "WHERE legacy_status IS NOT NULL AND status IN ('replied', 'won', 'lost')"
    )
    for new, old in _BACKWARD.items():
        op.execute(
            sa.text("UPDATE crm_leads SET status = :old WHERE status = :new").bindparams(old=old, new=new)
        )
    op.drop_index("ix_crm_leads_lost_reason", table_name="crm_leads")
    for col in ("legacy_status", "lost_reason", "lost_at", "won_at", "quoted_at"):
        op.drop_column("crm_leads", col)
