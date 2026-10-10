"""Notification Engine data models — devices, records, preferences, delivery logs."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from porterchain_api.db import Base


def _uuid() -> str:
    return str(uuid4())


class NotificationDeliveryLog(Base):
    """Per-attempt delivery trace (worker)."""

    __tablename__ = "notification_delivery_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    notification_id: Mapped[str | None] = mapped_column(String(36), index=True, nullable=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)
    template: Mapped[str] = mapped_column(String(64), index=True)
    recipient: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(32), default="sent")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationDevice(Base):
    """FCM device registration — one row per token."""

    __tablename__ = "notification_devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_role: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    platform: Mapped[str] = mapped_column(String(16), index=True)
    device_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    os_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fcm_token: Mapped[str] = mapped_column(String(512), index=True)
    language: Mapped[str] = mapped_column(String(16), default="en-CA")
    timezone: Mapped[str] = mapped_column(String(64), default="America/Toronto")
    notification_permission: Mapped[str] = mapped_column(String(16), default="default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationRecord(Base):
    """Enterprise notification audit + in-app center."""

    __tablename__ = "notification_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    event_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    template_key: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(32), default="operational", index=True)
    channel: Mapped[str] = mapped_column(String(16), index=True)
    priority: Mapped[str] = mapped_column(String(16), default="normal", index=True)
    recipient_type: Mapped[str] = mapped_column(String(32), index=True)
    recipient_id: Mapped[str] = mapped_column(String(36), index=True)
    recipient_address: Mapped[str | None] = mapped_column(String(512), nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    html_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    deep_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, default=5)
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context: Mapped[dict] = mapped_column(JSON, default=dict)
    search_tags: Mapped[dict] = mapped_column(JSON, default=dict)
    is_sandbox: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Provider tracking (ZeptoMail request id / client_reference) and webhook outcome.
    provider_message_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    delivery_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bounced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: event|correlation|template|channel|recipient. One row per key (unique partial index).
    idempotency_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Cross-path dedupe / rate-limit bucket, e.g. "delivered|<order>|<email>" or "eta|<email>".
    dedupe_family: Mapped[str | None] = mapped_column(String(160), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        Index(
            "uq_notification_records_idem_col",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
    )


class NotificationPreference(Base):
    """Per-user channel × category preferences."""

    __tablename__ = "notification_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_role: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    category: Mapped[str] = mapped_column(String(32), index=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    push_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    sms_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationUserSettings(Base):
    """Per-user quiet hours / timezone (Phase 3)."""

    __tablename__ = "notification_user_settings"
    __table_args__ = (UniqueConstraint("user_role", "user_id", name="uq_notification_user_settings_role_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_role: Mapped[str] = mapped_column(String(32), index=True)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    quiet_hours_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    quiet_start_hour: Mapped[int] = mapped_column(Integer, default=22)
    quiet_end_hour: Mapped[int] = mapped_column(Integer, default=7)
    timezone: Mapped[str] = mapped_column(String(64), default="America/Toronto")
    #: Email language for customer-facing mail ("en" / "fr"); None = auto.
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    #: CASL express consent for marketing email: when and from where it was given.
    marketing_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marketing_consent_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class EmailSuppression(Base):
    """Addresses we must not email (hard bounce, complaint). Unsuppress keeps the row."""

    __tablename__ = "notification_email_suppressions"

    email: Mapped[str] = mapped_column(String(320), primary_key=True)
    reason: Mapped[str] = mapped_column(String(32), default="hard_bounce")
    source: Mapped[str] = mapped_column(String(32), default="zeptomail")
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    bounce_count: Mapped[int] = mapped_column(Integer, default=1)
    notification_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    released_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationTemplateCopy(Base):
    """Admin-edited subject / intro per template + language. Append-only versions."""

    __tablename__ = "notification_template_copy"
    __table_args__ = (UniqueConstraint("template_key", "lang", "version", name="uq_notification_template_copy_ver"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    template_key: Mapped[str] = mapped_column(String(64), index=True)
    lang: Mapped[str] = mapped_column(String(8), default="en")
    version: Mapped[int] = mapped_column(Integer, default=1)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    intro: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class NotificationAdminSetting(Base):
    """Small JSON settings for the notification center (matrix switches, digest)."""

    __tablename__ = "notification_admin_settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_by: Mapped[str | None] = mapped_column(String(320), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
