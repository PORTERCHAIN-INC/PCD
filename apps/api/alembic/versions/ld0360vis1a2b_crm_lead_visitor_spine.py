"""Lead360 P0 — CrmLead visitor_session_id + booking_draft_id spine.

Revision ID: ld0360vis1a2b
Revises: pg0gtacatalog1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "ld0360vis1a2b"
down_revision = "vc0snake1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_leads",
        sa.Column("visitor_session_id", sa.String(length=64), nullable=True),
    )
    op.create_index(
        "ix_crm_leads_visitor_session_id",
        "crm_leads",
        ["visitor_session_id"],
        unique=False,
    )
    op.add_column(
        "crm_leads",
        sa.Column("booking_draft_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_crm_leads_booking_draft_id",
        "crm_leads",
        ["booking_draft_id"],
        unique=False,
    )

    # Best-effort backfill from custom_fields (guide / prior stamps).
    op.execute(
        sa.text(
            """
            UPDATE crm_leads
            SET visitor_session_id = LEFT(
                COALESCE(
                    NULLIF(TRIM(custom_fields->>'visitor_id'), ''),
                    NULLIF(TRIM(custom_fields->>'session_id'), '')
                ),
                64
            )
            WHERE visitor_session_id IS NULL
              AND (
                NULLIF(TRIM(custom_fields->>'visitor_id'), '') IS NOT NULL
                OR NULLIF(TRIM(custom_fields->>'session_id'), '') IS NOT NULL
              )
            """
        )
    )

    # Link draft via quote_id when both sides exist.
    op.execute(
        sa.text(
            """
            UPDATE crm_leads c
            SET booking_draft_id = d.id
            FROM booking_drafts d
            WHERE c.booking_draft_id IS NULL
              AND c.quote_id IS NOT NULL
              AND d.quote_id = c.quote_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE crm_leads c
            SET booking_draft_id = d.id
            FROM booking_drafts d
            WHERE c.booking_draft_id IS NULL
              AND NULLIF(TRIM(c.custom_fields->>'quote_id'), '') IS NOT NULL
              AND d.quote_id = TRIM(c.custom_fields->>'quote_id')
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_crm_leads_booking_draft_id", table_name="crm_leads")
    op.drop_column("crm_leads", "booking_draft_id")
    op.drop_index("ix_crm_leads_visitor_session_id", table_name="crm_leads")
    op.drop_column("crm_leads", "visitor_session_id")
