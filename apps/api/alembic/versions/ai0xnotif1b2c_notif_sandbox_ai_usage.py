"""notification_records.is_sandbox + ai_usage_logs for NIM/LLM metering."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "ai0xnotif1b2c"
down_revision = "sb0x1y2z3a4b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notification_records",
        sa.Column("is_sandbox", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_notification_records_is_sandbox", "notification_records", ["is_sandbox"])

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("provider", sa.String(length=32), nullable=False, index=True),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("feature", sa.String(length=64), nullable=False, index=True),
        sa.Column("actor_type", sa.String(length=32), nullable=True),
        sa.Column("actor_id", sa.String(length=64), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ok"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_ai_usage_logs_created_at", "ai_usage_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_usage_logs_created_at", table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_index("ix_notification_records_is_sandbox", table_name="notification_records")
    op.drop_column("notification_records", "is_sandbox")
