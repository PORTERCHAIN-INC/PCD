"""Notification center: provider tracking columns, suppression list, template copy versions, admin settings."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "nt1notifcenter1a2b"
down_revision = "nt0emailnotif1a2b"
branch_labels = None
depends_on = None

_TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.add_column("notification_records", sa.Column("provider_message_id", sa.String(length=128), nullable=True))
    op.add_column("notification_records", sa.Column("delivery_status", sa.String(length=32), nullable=True))
    op.add_column("notification_records", sa.Column("bounced_at", _TS, nullable=True))
    op.create_index(
        "ix_notification_records_provider_message_id", "notification_records", ["provider_message_id"]
    )

    op.create_table(
        "notification_email_suppressions",
        sa.Column("email", sa.String(length=320), primary_key=True),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("bounce_count", sa.Integer(), nullable=False),
        sa.Column("notification_id", sa.String(length=36), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("released_by", sa.String(length=320), nullable=True),
        sa.Column("released_at", _TS, nullable=True),
        sa.Column("created_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _TS, server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_notification_email_suppressions_active", "notification_email_suppressions", ["active"]
    )
    # Carry over addresses already marked bounced on notification rows.
    op.execute(
        """
        INSERT INTO notification_email_suppressions (email, reason, source, active, bounce_count, created_at, updated_at)
        SELECT LOWER(TRIM(recipient_address)), 'hard_bounce', 'backfill', TRUE, COUNT(*), MIN(created_at), NOW()
        FROM notification_records
        WHERE channel = 'email' AND status = 'bounced' AND recipient_address LIKE '%@%'
        GROUP BY LOWER(TRIM(recipient_address))
        ON CONFLICT (email) DO NOTHING
        """
    )

    op.create_table(
        "notification_template_copy",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("lang", sa.String(length=8), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("intro", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.String(length=320), nullable=True),
        sa.Column("created_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("template_key", "lang", "version", name="uq_notification_template_copy_ver"),
    )
    op.create_index("ix_notification_template_copy_template_key", "notification_template_copy", ["template_key"])

    op.create_table(
        "notification_admin_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.String(length=320), nullable=True),
        sa.Column("updated_at", _TS, server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notification_admin_settings")
    op.drop_index("ix_notification_template_copy_template_key", table_name="notification_template_copy")
    op.drop_table("notification_template_copy")
    op.drop_index("ix_notification_email_suppressions_active", table_name="notification_email_suppressions")
    op.drop_table("notification_email_suppressions")
    op.drop_index("ix_notification_records_provider_message_id", table_name="notification_records")
    op.drop_column("notification_records", "bounced_at")
    op.drop_column("notification_records", "delivery_status")
    op.drop_column("notification_records", "provider_message_id")
