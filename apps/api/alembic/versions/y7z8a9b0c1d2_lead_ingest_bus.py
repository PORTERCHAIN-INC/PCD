"""CRM lead ingest bus: channel/intent/decision + identities + conversations."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "y7z8a9b0c1d2"
down_revision = "ai0xnotif1b2c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crm_leads",
        sa.Column("channel", sa.String(length=64), nullable=False, server_default="website"),
    )
    op.add_column(
        "crm_leads",
        sa.Column("intent_type", sa.String(length=32), nullable=False, server_default="merchant"),
    )
    op.add_column(
        "crm_leads",
        sa.Column("decision_status", sa.String(length=32), nullable=False, server_default="new"),
    )
    op.add_column("crm_leads", sa.Column("referred_by_merchant_id", sa.String(length=36), nullable=True))
    op.add_column("crm_leads", sa.Column("merge_candidate_of", sa.String(length=36), nullable=True))
    op.add_column(
        "crm_leads",
        sa.Column("sla_first_response_due_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_leads",
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "crm_leads",
        sa.Column(
            "consent",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_crm_leads_channel", "crm_leads", ["channel"])
    op.create_index("ix_crm_leads_intent_type", "crm_leads", ["intent_type"])
    op.create_index("ix_crm_leads_decision_status", "crm_leads", ["decision_status"])
    op.create_index("ix_crm_leads_referred_by_merchant_id", "crm_leads", ["referred_by_merchant_id"])
    op.create_index("ix_crm_leads_merge_candidate_of", "crm_leads", ["merge_candidate_of"])

    op.create_table(
        "crm_lead_ingest_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("external_event_id", sa.String(length=255), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=True),
        sa.Column("lead_id", sa.String(length=36), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="processed"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("provider", "external_event_id", name="uq_crm_lead_ingest_provider_ext"),
    )
    op.create_index("ix_crm_lead_ingest_events_provider", "crm_lead_ingest_events", ["provider"])
    op.create_index("ix_crm_lead_ingest_events_lead_id", "crm_lead_ingest_events", ["lead_id"])
    op.create_index("ix_crm_lead_ingest_events_status", "crm_lead_ingest_events", ["status"])

    op.create_table(
        "crm_lead_identities",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("value_normalized", sa.String(length=320), nullable=False),
        sa.Column("raw_value", sa.String(length=512), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("kind", "value_normalized", name="uq_crm_lead_identity_kind_value"),
    )
    op.create_index("ix_crm_lead_identities_lead_id", "crm_lead_identities", ["lead_id"])
    op.create_index("ix_crm_lead_identities_kind", "crm_lead_identities", ["kind"])

    op.create_table(
        "crm_conversations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("lead_id", sa.String(length=36), sa.ForeignKey("crm_leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("channel", sa.String(length=64), nullable=False),
        sa.Column("external_thread_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_crm_conversations_lead_id", "crm_conversations", ["lead_id"])
    op.create_index("ix_crm_conversations_channel", "crm_conversations", ["channel"])
    op.create_index("ix_crm_conversations_external_thread_id", "crm_conversations", ["external_thread_id"])
    op.create_index("ix_crm_conversations_status", "crm_conversations", ["status"])

    op.create_table(
        "crm_conversation_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("crm_conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=16), nullable=False, server_default="inbound"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("actor_type", sa.String(length=32), nullable=False, server_default="prospect"),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_crm_conversation_messages_conversation_id",
        "crm_conversation_messages",
        ["conversation_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_crm_conversation_messages_conversation_id", table_name="crm_conversation_messages")
    op.drop_table("crm_conversation_messages")
    op.drop_index("ix_crm_conversations_status", table_name="crm_conversations")
    op.drop_index("ix_crm_conversations_external_thread_id", table_name="crm_conversations")
    op.drop_index("ix_crm_conversations_channel", table_name="crm_conversations")
    op.drop_index("ix_crm_conversations_lead_id", table_name="crm_conversations")
    op.drop_table("crm_conversations")
    op.drop_index("ix_crm_lead_identities_kind", table_name="crm_lead_identities")
    op.drop_index("ix_crm_lead_identities_lead_id", table_name="crm_lead_identities")
    op.drop_table("crm_lead_identities")
    op.drop_index("ix_crm_lead_ingest_events_status", table_name="crm_lead_ingest_events")
    op.drop_index("ix_crm_lead_ingest_events_lead_id", table_name="crm_lead_ingest_events")
    op.drop_index("ix_crm_lead_ingest_events_provider", table_name="crm_lead_ingest_events")
    op.drop_table("crm_lead_ingest_events")
    op.drop_index("ix_crm_leads_merge_candidate_of", table_name="crm_leads")
    op.drop_index("ix_crm_leads_referred_by_merchant_id", table_name="crm_leads")
    op.drop_index("ix_crm_leads_decision_status", table_name="crm_leads")
    op.drop_index("ix_crm_leads_intent_type", table_name="crm_leads")
    op.drop_index("ix_crm_leads_channel", table_name="crm_leads")
    op.drop_column("crm_leads", "consent")
    op.drop_column("crm_leads", "last_touch_at")
    op.drop_column("crm_leads", "sla_first_response_due_at")
    op.drop_column("crm_leads", "merge_candidate_of")
    op.drop_column("crm_leads", "referred_by_merchant_id")
    op.drop_column("crm_leads", "decision_status")
    op.drop_column("crm_leads", "intent_type")
    op.drop_column("crm_leads", "channel")
