"""CRM referral credits + LinkedIn/X/YouTube channel events (P2)."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "z8a9b0c1d2e3"
down_revision = "y7z8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crm_referral_credits",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("referring_merchant_id", sa.String(length=36), nullable=False),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column("company_id", sa.String(length=36), nullable=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_crm_referral_credits_referring_merchant_id",
        "crm_referral_credits",
        ["referring_merchant_id"],
    )
    op.create_index("ix_crm_referral_credits_lead_id", "crm_referral_credits", ["lead_id"])
    op.create_index("ix_crm_referral_credits_company_id", "crm_referral_credits", ["company_id"])
    op.create_index("ix_crm_referral_credits_status", "crm_referral_credits", ["status"])


def downgrade() -> None:
    op.drop_index("ix_crm_referral_credits_status", table_name="crm_referral_credits")
    op.drop_index("ix_crm_referral_credits_company_id", table_name="crm_referral_credits")
    op.drop_index("ix_crm_referral_credits_lead_id", table_name="crm_referral_credits")
    op.drop_index(
        "ix_crm_referral_credits_referring_merchant_id", table_name="crm_referral_credits"
    )
    op.drop_table("crm_referral_credits")
