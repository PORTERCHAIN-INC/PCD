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
from porterchain_api.notification_engine.templates import render_template
from porterchain_shared.config.settings import get_platform_settings

logger = logging.getLogger(__name__)


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
            return log
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
        subject, body = render_template(template, context)
        if not settings.smtp_host:
            logger.info("email (log-only): to=%s template=%s", recipient, template)
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        from_addr = settings.smtp_from_for(context.get("from_alias") or context.get("mail_from"))
        from_name = context.get("from_name") or settings.smtp_from_name
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = recipient
        msg.set_content(body)
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as smtp:
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(msg)

    def _send_sms(self, recipient: str, template: str, context: dict[str, Any]) -> None:
        if not recipient:
            raise ValueError("sms_recipient_required")
        _, body = render_template(template, context)
        logger.info("sms (log-only): to=%s template=%s body=%s", recipient, template, body[:160])

    def _send_push(
        self,
        token: str,
        template: str,
        context: dict[str, Any],
        *,
        recipient_type: str,
        recipient_id: str,
    ) -> None:
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
