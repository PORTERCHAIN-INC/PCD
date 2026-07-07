"""Merchant integrations — API usage logs, webhook delivery history.

Revision ID: g8h9i0j1k2l3
Revises: f7a8b9c0d1e2
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "g8h9i0j1k2l3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "merchant_webhooks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_table(
        "merchant_api_usage_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("api_key_id", sa.String(length=36), nullable=False),
        sa.Column("method", sa.String(length=16), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("environment", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["merchant_api_keys.id"]),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_api_usage_logs_merchant_id", "merchant_api_usage_logs", ["merchant_id"])
    op.create_index("ix_merchant_api_usage_logs_api_key_id", "merchant_api_usage_logs", ["api_key_id"])
    op.create_index("ix_merchant_api_usage_logs_path", "merchant_api_usage_logs", ["path"])
    op.create_index("ix_merchant_api_usage_logs_created_at", "merchant_api_usage_logs", ["created_at"])
    op.create_table(
        "merchant_webhook_deliveries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("merchant_id", sa.String(length=36), nullable=False),
        sa.Column("webhook_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("request_body", sa.JSON(), nullable=False),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.String(length=512), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["merchant_id"], ["merchants.id"]),
        sa.ForeignKeyConstraint(["webhook_id"], ["merchant_webhooks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_merchant_webhook_deliveries_merchant_id", "merchant_webhook_deliveries", ["merchant_id"])
    op.create_index("ix_merchant_webhook_deliveries_webhook_id", "merchant_webhook_deliveries", ["webhook_id"])
    op.create_index("ix_merchant_webhook_deliveries_event_type", "merchant_webhook_deliveries", ["event_type"])
    op.create_index("ix_merchant_webhook_deliveries_created_at", "merchant_webhook_deliveries", ["created_at"])


def downgrade() -> None:
    op.drop_table("merchant_webhook_deliveries")
    op.drop_table("merchant_api_usage_logs")
    op.drop_column("merchant_webhooks", "updated_at")
