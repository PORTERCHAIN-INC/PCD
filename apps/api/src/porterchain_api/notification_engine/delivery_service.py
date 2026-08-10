"""Notification delivery — SMTP, FCM with durable delivery logs."""

from __future__ import annotations

import logging
import smtplib
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

from porterchain_api.db import SessionLocal
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.notification_engine.fcm_service import FCMService
from porterchain_api.notification_engine.models import NotificationDeliveryLog, NotificationRecord
from porterchain_api.notification_engine.templates import render_email, render_template
from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)


class DeliveryDeferred(Exception):
    """Channel accepted for audit but not actually delivered (disabled / log-only)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _normalize_recipient(payload: dict[str, Any]) -> str:
    raw = payload.get("recipient")
    if isinstance(raw, str):
        return raw
    if isinstance(raw, dict):
        return raw.get("email") or raw.get("phone") or raw.get("token") or ""
    return payload.get("email") or payload.get("phone") or ""


class DeliveryService:
    def deliver(self, payload: dict[str, Any]) -> NotificationDeliveryLog:
        channel = payload.get("channel", "email")
        template = payload.get("template", "delivery_update")
        notification_id = payload.get("notification_id")
        recipient_type = payload.get("recipient_type", "")
        recipient_id = payload.get("recipient_id", "")
        recipient = _normalize_recipient(payload)
        context = payload.get("context") or {}
        status = "sent"
        error: str | None = None

        if notification_id and self._already_delivered(notification_id):
            db = SessionLocal()
            try:
                log = NotificationDeliveryLog(
                    notification_id=notification_id,
                    channel=channel,
                    template=template,
                    recipient=recipient[:320] if recipient else recipient_type,
                    status="skipped",
                    error="already_sent",
                    context=context,
                )
                db.add(log)
                db.commit()
                db.refresh(log)
                return log
            finally:
                db.close()

        try:
            if channel == "email":
                self._send_email(recipient, template, context)
            elif channel == "sms":
                self._send_sms(recipient, template, context)
            elif channel == "push":
                self._send_push(
                    recipient,
                    template,
                    context,
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                )
            else:
                raise ValueError(f"unknown_channel:{channel}")
        except DeliveryDeferred as exc:
            # D-6: do not claim "sent" for log-only / disabled channels.
            status = "logged"
            error = exc.reason
            logger.info("notification delivery deferred (%s): %s", channel, exc.reason)
        except Exception as exc:  # noqa: BLE001
            status = "failed"
            error = str(exc)
            logger.warning("notification delivery failed: %s", exc)
            if notification_id:
                self._mark_failed(notification_id, error, schedule_retry=True)

        db = SessionLocal()
        try:
            if notification_id and status == "sent":
                self._mark_sent(db, notification_id)

            log = NotificationDeliveryLog(
                notification_id=notification_id,
                channel=channel,
                template=template,
                recipient=recipient[:320] if recipient else recipient_type,
                status=status,
                error=error,
                context=context,
            )
            db.add(log)
            db.commit()
            db.refresh(log)
            if status == "failed" and channel in ("push", "sms"):
                self._try_channel_fallback(payload, failed_channel=channel)
            return log
        finally:
            db.close()

    def _try_channel_fallback(self, payload: dict[str, Any], *, failed_channel: str) -> None:
        """push → sms → email when addresses/prefs allow (Phase 3)."""
        chain = {"push": ("sms", "email"), "sms": ("email",)}.get(failed_channel, ())
        if not chain:
            return
        context = dict(payload.get("context") or {})
        recipient_type = str(payload.get("recipient_type") or "")
        recipient_id = str(payload.get("recipient_id") or "")
        template = str(payload.get("template") or "delivery_update")
        notification_id = payload.get("notification_id")

        phone = context.get("phone") or context.get("sms") or context.get("contact_phone")
        email = context.get("email") or context.get("contact_email")
        if notification_id and not email:
            db = SessionLocal()
            try:
                row = db.get(NotificationRecord, notification_id)
                if row and row.recipient_address and "@" in (row.recipient_address or ""):
                    email = row.recipient_address
                if row:
                    context.setdefault("title", row.title)
                    context.setdefault("body", row.body)
                    context.setdefault("deep_link", row.deep_link)
            finally:
                db.close()

        from porterchain_api.notification_engine.engine import get_notification_engine
        from porterchain_api.notification_engine.preference_service import PreferenceService
        from porterchain_api.notification_engine.user_settings import UserSettingsService

        prefs = PreferenceService()
        quiet = UserSettingsService()
        engine = get_notification_engine()
        category = str(context.get("category") or "operational")

        db = SessionLocal()
        try:
            if notification_id:
                row = db.get(NotificationRecord, notification_id)
                if row:
                    category = row.category or category
            for next_channel in chain:
                address = phone if next_channel == "sms" else email if next_channel == "email" else None
                if not address:
                    continue
                if not prefs.is_enabled(
                    db,
                    user_role=recipient_type or "customer",
                    user_id=recipient_id or "unknown",
                    category=category,
                    channel=next_channel,
                ):
                    continue
                if quiet.should_mute_channel(
                    db,
                    user_role=recipient_type or "customer",
                    user_id=recipient_id or "unknown",
                    channel=next_channel,
                    priority=str(context.get("priority") or "normal"),
                    category=category,
                ):
                    continue
                rec = engine.dispatch(
                    db,
                    event_type="notification.channel_fallback",
                    template_key=template,
                    channel=next_channel,
                    recipient_type=recipient_type or "customer",
                    recipient_id=recipient_id or "unknown",
                    recipient_address=str(address),
                    context={**context, "fallback_from": failed_channel},
                    category=category,
                    search_tags={"fallback_from": failed_channel, "source_notification_id": notification_id},
                    correlation_id=f"fallback:{notification_id}:{next_channel}",
                )
                if rec:
                    db.commit()
                    logger.info(
                        "channel fallback queued: %s → %s notification=%s",
                        failed_channel,
                        next_channel,
                        rec.id,
                    )
                    return
            db.rollback()
        except Exception:  # noqa: BLE001
            logger.exception("channel fallback failed")
            db.rollback()
        finally:
            db.close()

    @staticmethod
    def _already_delivered(notification_id: str) -> bool:
        db = SessionLocal()
        try:
            row = db.get(NotificationRecord, notification_id)
            return bool(row and row.status in ("sent", "delivered"))
        finally:
            db.close()

    def _mark_sent(self, db, notification_id: str) -> None:
        row = db.get(NotificationRecord, notification_id)
        if not row:
            return
        now = datetime.now(UTC)
        row.status = "delivered" if row.channel == "push" else "sent"
        row.sent_at = row.sent_at or now
        row.delivered_at = now
        db.flush()
        from porterchain_shared.events.catalog import DomainEventType

        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_SENT,
            aggregate_type="notification",
            aggregate_id=notification_id,
            correlation_id=row.event_type or notification_id,
            payload={
                "channel": row.channel,
                "template": row.template_key,
                "notification_id": notification_id,
            },
        )
        db.commit()

    def _mark_failed(self, notification_id: str, error: str, *, schedule_retry: bool) -> None:
        from porterchain_api.notification_engine.engine import get_notification_engine

        db = SessionLocal()
        try:
            row = db.get(NotificationRecord, notification_id)
            if not row:
                return
            if schedule_retry:
                get_notification_engine().schedule_retry(db, row, error)
            else:
                row.status = "failed"
                row.failure_reason = error
            db.commit()
        finally:
            db.close()

    def _send_email(self, recipient: str, template: str, context: dict[str, Any]) -> None:
        if not recipient:
            raise ValueError("email_recipient_required")
        settings = get_platform_settings()
        subject, text_body, html_body = render_email(template, context)
        if not settings.smtp_host:
            logger.info("email (log-only): to=%s template=%s", recipient, template)
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        from_addr = settings.smtp_from_for(context.get("from_alias") or context.get("mail_from"))
        from_name = context.get("from_name") or settings.smtp_from_name or "PorterChain"
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = recipient
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        host = settings.smtp_host
        port = int(settings.smtp_port or 587)
        # Local stack: always use Mailpit so payment/invoice receipts are inspectable
        # without sending through production Zoho.
        if str(getattr(settings, "app_env", "")).lower() in {"local", "development", "dev"}:
            host, port = "localhost", 1025

        # Mailpit / local: plain SMTP (1025). Prod Zoho: SMTP_SSL (465) with login.
        use_ssl = port not in (25, 587, 1025) and bool(settings.smtp_user)
        if use_ssl:
            with smtplib.SMTP_SSL(host, port) as smtp:
                smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as smtp:
                if port == 587:
                    smtp.starttls()
                if settings.smtp_user and port != 1025:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)

    def _send_sms(self, recipient: str, template: str, context: dict[str, Any]) -> None:
        if not recipient:
            raise ValueError("sms_recipient_required")
        settings = get_platform_settings()
        _, body = render_template(template, context)
        if not getattr(settings, "sms_enabled", False):
            logger.info(
                "sms (disabled — set PORTERCHAIN_SMS_ENABLED): to=%s template=%s body=%s",
                recipient,
                template,
                body[:160],
            )
            raise DeliveryDeferred("sms_disabled")
        # Provider adapters (Twilio/MessageBird) land here when sms_enabled is true.
        provider = (getattr(settings, "sms_provider", "") or "").strip().lower()
        if not provider:
            logger.info("sms (log-only, no provider): to=%s template=%s body=%s", recipient, template, body[:160])
            raise DeliveryDeferred("sms_provider_missing")
        raise ValueError(f"sms_provider_not_configured:{provider}")

    def _send_push(
        self,
        token: str,
        template: str,
        context: dict[str, Any],
        *,
        recipient_type: str,
        recipient_id: str,
    ) -> None:
        from porterchain_api.notification_engine.fcm_service import firebase_credentials_configured

        settings = get_platform_settings()
        if not getattr(settings, "push_enabled", True):
            raise DeliveryDeferred("push_disabled")
        if not getattr(settings, "push_send", True) or not firebase_credentials_configured():
            # Still resolve tokens for diagnostics, but do not claim real delivery (D-6).
            title = context.get("title") or render_template(template, context)[0]
            logger.info(
                "push (log-only): recipient=%s/%s title=%s",
                recipient_type,
                recipient_id,
                title,
            )
            raise DeliveryDeferred("push_log_only")

        title = context.get("title") or render_template(template, context)[0]
        body = context.get("body") or render_template(template, context)[1]
        deep_link = context.get("deep_link")
        fcm = FCMService()
        devices = DeviceService()

        db = SessionLocal()
        try:
            tokens: list[str] = []
            if token:
                tokens = [token]
            elif recipient_type and recipient_id:
                tokens = [d.fcm_token for d in devices.list_active(db, user_role=recipient_type, user_id=recipient_id)]
            if not tokens:
                raise ValueError("push_token_required")

            failures = 0
            for t in tokens:
                ok, err, invalid = fcm.send(t, title=str(title), body=str(body), data=context, deep_link=deep_link)
                if invalid:
                    devices.invalidate_token(db, t)
                if not ok:
                    failures += 1
                    logger.warning("FCM failed token=%s err=%s", t[:16], err)
            db.commit()
            if failures == len(tokens):
                raise ValueError("push_all_tokens_failed")
        finally:
            db.close()


def deliver_notification(payload: dict[str, Any]) -> None:
    DeliveryService().deliver(payload)
