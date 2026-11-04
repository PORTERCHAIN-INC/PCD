"""Pricing admin (doc 72 §9.5): rate cards, versions, org pricing mode, audit."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "pr72ratecards01"
down_revision = "kc8authsubject0008"
branch_labels = None
depends_on = None


def _now() -> sa.TextClause:
    return sa.text("now()")


def upgrade() -> None:
    op.create_table(
        "pricing_rate_cards",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("org_id", sa.String(36), nullable=True),
        sa.Column("contract_document_id", sa.String(36), nullable=True),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
    )
    op.create_index("ix_pricing_rate_cards_org_id", "pricing_rate_cards", ["org_id"])
    op.create_table(
        "pricing_rate_card_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "rate_card_id",
            sa.String(36),
            sa.ForeignKey("pricing_rate_cards.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lines", sa.JSON(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("published_by", sa.String(36), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
        sa.UniqueConstraint("rate_card_id", "version", name="uq_pricing_rate_card_version"),
    )
    op.create_index("ix_pricing_rate_card_versions_rate_card_id", "pricing_rate_card_versions", ["rate_card_id"])
    op.create_index("ix_pricing_rate_card_versions_status", "pricing_rate_card_versions", ["status"])
    op.create_table(
        "pricing_org_pricing",
        sa.Column("org_id", sa.String(36), primary_key=True),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("preset_pct", sa.Float(), nullable=True),
        sa.Column("preset_per_stop_cents", sa.Integer(), nullable=True),
        sa.Column("band_overrides", sa.JSON(), nullable=True),
        sa.Column(
            "rate_card_id",
            sa.String(36),
            sa.ForeignKey("pricing_rate_cards.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("contract_document_id", sa.String(36), nullable=True),
        sa.Column("red_reason", sa.Text(), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
    )
    op.create_table(
        "pricing_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=True),
        sa.Column("actor_id", sa.String(36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_now(), nullable=False),
    )
    op.create_index("ix_pricing_audit_entity", "pricing_audit", ["entity"])
    op.create_index("ix_pricing_audit_entity_id", "pricing_audit", ["entity_id"])
    op.create_index("ix_pricing_audit_created_at", "pricing_audit", ["created_at"])


def downgrade() -> None:
    op.drop_table("pricing_audit")
    op.drop_table("pricing_org_pricing")
    op.drop_table("pricing_rate_card_versions")
    op.drop_table("pricing_rate_cards")
