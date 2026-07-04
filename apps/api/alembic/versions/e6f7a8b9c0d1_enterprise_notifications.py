"""Enterprise notification engine tables.

Revision ID: e6f7a8b9c0d1
Revises: d5f6a7b8c9d0
Create Date: 2026-06-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "notification_delivery_logs",
        sa.Column("notification_id", sa.String(length=36), nullable=True),
    )
    op.create_index(
        "ix_notification_delivery_logs_notification_id",
        "notification_delivery_logs",
        ["notification_id"],
    )

    op.create_table(
        "notification_devices",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_role", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("device_name", sa.String(length=128), nullable=True),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("os_version", sa.String(length=64), nullable=True),
        sa.Column("fcm_token", sa.String(length=512), nullable=False),
        sa.Column("language", sa.String(length=16), server_default="en-CA", nullable=False),
        sa.Column("timezone", sa.String(length=64), server_default="America/Toronto", nullable=False),
        sa.Column("notification_permission", sa.String(length=16), server_default="default", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notification_devices_user_role", "notification_devices", ["user_role"])
    op.create_index("ix_notification_devices_user_id", "notification_devices", ["user_id"])
    op.create_index("ix_notification_devices_platform", "notification_devices", ["platform"])
    op.create_index("ix_notification_devices_fcm_token", "notification_devices", ["fcm_token"])
    op.create_index("ix_notification_devices_is_active", "notification_devices", ["is_active"])

    op.create_table(
        "notification_records",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=64), nullable=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("category", sa.String(length=32), server_default="operational", nullable=False),
        sa.Column("channel", sa.String(length=16), nullable=False),
        sa.Column("priority", sa.String(length=16), server_default="normal", nullable=False),
        sa.Column("recipient_type", sa.String(length=32), nullable=False),
        sa.Column("recipient_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_address", sa.String(length=512), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("html_body", sa.Text(), nullable=True),
        sa.Column("deep_link", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_retries", sa.Integer(), server_default="5", nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("context", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("search_tags", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("is_read", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("clicked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    for col in (
        "event_type",
        "template_key",
        "category",
        "channel",
        "priority",
        "recipient_type",
        "recipient_id",
        "status",
        "is_read",
        "is_archived",
    ):
        op.create_index(f"ix_notification_records_{col}", "notification_records", [col])

    op.create_table(
        "notification_preferences",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_role", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("push_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sms_enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("in_app_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_notification_preferences_user_role", "notification_preferences", ["user_role"])
    op.create_index("ix_notification_preferences_user_id", "notification_preferences", ["user_id"])
    op.create_index("ix_notification_preferences_category", "notification_preferences", ["category"])


def downgrade() -> None:
    op.drop_table("notification_preferences")
    op.drop_table("notification_records")
    op.drop_table("notification_devices")
    op.drop_index("ix_notification_delivery_logs_notification_id", table_name="notification_delivery_logs")
    op.drop_column("notification_delivery_logs", "notification_id")
