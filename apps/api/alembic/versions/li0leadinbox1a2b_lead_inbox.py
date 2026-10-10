"""Unified lead inbox: reply state, booking link, newsletter subscribers.

Adds to `crm_leads`: `awaiting_reply`, `last_inbound_at`, `first_response_at`,
`order_id`. Adds `channel` + `delivery_status` to `crm_conversation_messages`
plus a partial unique index on `external_message_id` (inbound email / WhatsApp
idempotency). Creates `marketing_subscribers` (double opt-in list kept apart
from sales leads).

Revision ID: li0leadinbox1a2b
Revises: pb0pricebook1a2b
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "li0leadinbox1a2b"
down_revision = "pb0pricebook1a2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_leads",
        sa.Column("awaiting_reply", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("crm_leads", sa.Column("last_inbound_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_leads", sa.Column("first_response_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("crm_leads", sa.Column("order_id", sa.String(36), nullable=True))
    op.create_index("ix_crm_leads_awaiting_reply", "crm_leads", ["awaiting_reply"])
    op.create_index("ix_crm_leads_order_id", "crm_leads", ["order_id"])

    op.add_column("crm_conversation_messages", sa.Column("channel", sa.String(64), nullable=True))
    op.add_column(
        "crm_conversation_messages", sa.Column("delivery_status", sa.String(32), nullable=True)
    )
    op.create_index(
        "uq_crm_conv_msg_external_id",
        "crm_conversation_messages",
        ["external_message_id"],
        unique=True,
        postgresql_where=sa.text("external_message_id IS NOT NULL"),
    )

    op.create_table(
        "marketing_subscribers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("confirm_token_hash", sa.String(64), nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
        sa.Column("source_page", sa.String(512), nullable=True),
        sa.Column("locale", sa.String(8), nullable=True),
        sa.Column("consent", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("attribution", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("lead_id", sa.String(36), nullable=True),
        sa.Column("confirm_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_marketing_subscribers_email", "marketing_subscribers", ["email"], unique=True)
    op.create_index("ix_marketing_subscribers_status", "marketing_subscribers", ["status"])
    op.create_index(
        "ix_marketing_subscribers_confirm_token_hash", "marketing_subscribers", ["confirm_token_hash"]
    )


def downgrade() -> None:
    op.drop_index("ix_marketing_subscribers_confirm_token_hash", table_name="marketing_subscribers")
    op.drop_index("ix_marketing_subscribers_status", table_name="marketing_subscribers")
    op.drop_index("ix_marketing_subscribers_email", table_name="marketing_subscribers")
    op.drop_table("marketing_subscribers")
    op.drop_index("uq_crm_conv_msg_external_id", table_name="crm_conversation_messages")
    op.drop_column("crm_conversation_messages", "delivery_status")
    op.drop_column("crm_conversation_messages", "channel")
    op.drop_index("ix_crm_leads_order_id", table_name="crm_leads")
    op.drop_index("ix_crm_leads_awaiting_reply", table_name="crm_leads")
    op.drop_column("crm_leads", "order_id")
    op.drop_column("crm_leads", "first_response_at")
    op.drop_column("crm_leads", "last_inbound_at")
    op.drop_column("crm_leads", "awaiting_reply")
