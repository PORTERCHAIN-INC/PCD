"""Notification delivery — SMTP, FCM with durable delivery logs."""

from __future__ import annotations

import logging
import smtplib
import ssl
from datetime import UTC, datetime
from email.message import EmailMessage
from typing import Any

from porterchain_api.db import SessionLocal
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.notification_engine.device_service import DeviceService
from porterchain_api.notification_engine.internal_inbox_mail import (
    normalize_recipient,
    record_internal_inbox_skip,
)
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


class DeliveryService:
    def deliver(self, payload: dict[str, Any]) -> NotificationDeliveryLog:
        from porterchain_api.notification_engine import send_claim

        nid = payload.get("notification_id")
        ok, previous = send_claim.claim(nid) if nid else (True, None)
        if not ok:  # another worker owns it, or it already went out
            return self._write_log(nid, payload.get("channel", "email"), payload.get("template", ""), payload.get("recipient") or "", "skipped", "already_sent", payload.get("context") or {})
        try:
            return self._deliver(payload)
        finally:
            if nid:
                send_claim.release(nid, previous)

    def _deliver(self, payload: dict[str, Any]) -> NotificationDeliveryLog:
        channel = payload.get("channel", "email")
        template = payload.get("template", "delivery_update")
        notification_id = payload.get("notification_id")
        recipient_type = payload.get("recipient_type", "")
        recipient_id = payload.get("recipient_id", "")
        recipient = normalize_recipient(payload)
        context = payload.get("context") or {}
        status = "sent"
        error: str | None = None
        is_sandbox = bool(context.get("is_sandbox") is True)
        if is_sandbox and channel in ("push", "sms") and not context.get("allow_sandbox_delivery"):
            status = "deferred"
            error = "sandbox_push_sms_blocked"
            logger.info("sandbox blocks %s delivery (notification_id=%s)", channel, notification_id)
            if notification_id:
                self._mark_deferred(notification_id, error)
            return self._write_log(
                notification_id, channel, template, recipient or recipient_type, status, error,
                {**context, "is_sandbox": True},
            )
        if channel == "email" and template == "lead_sla_escalation":
            from porterchain_api.notification_engine.staff_fanout import ops_watch_emails

            address = (recipient or "").strip().lower()
            watch = ops_watch_emails()
            if not context.get("offline_watch") or not address or address not in watch:
                return record_internal_inbox_skip(
                    notification_id, channel, template, recipient, recipient_type, context, self._mark_deferred
                )

        try:
            if channel == "email":
                who = {"recipient_type": recipient_type, "recipient_id": recipient_id, "notification_id": notification_id}
                self._send_email(recipient, template, {**context, **who})
            elif channel == "sms":
                self._send_sms(recipient, template, context)
            elif channel == "push":
                self._send_push(
                    recipient,
                    template,
                    {**context, "notification_id": notification_id, "priority": context.get("priority") or "normal"},
                    recipient_type=recipient_type,
                    recipient_id=recipient_id,
                )
            else:
                raise ValueError(f"unknown_channel:{channel}")
        except DeliveryDeferred as exc:
            # D-6 / Phase 2.5b: terminal honesty — do not claim sent; do not retry.
            status = "deferred"
            error = exc.reason
            logger.info("notification delivery deferred (%s): %s", channel, exc.reason)
            if notification_id:
                self._mark_deferred(notification_id, error)
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

    @staticmethod
    def _write_log(notification_id, channel, template, recipient, status, error, context) -> NotificationDeliveryLog:
        db = SessionLocal()
        try:
            log = NotificationDeliveryLog(
                notification_id=notification_id, channel=channel, template=template,
                recipient=(recipient or "")[:320], status=status, error=error, context=context,
            )
            db.add(log)
            db.commit()
            db.refresh(log)
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
        if notification_id:
            db = SessionLocal()
            try:
                row = db.get(NotificationRecord, notification_id)
                if row and row.recipient_address and "@" in (row.recipient_address or ""):
                    email = email or row.recipient_address
                if row:
                    context.setdefault("title", row.title)
                    context.setdefault("body", row.body)
                    context.setdefault("deep_link", row.deep_link)
                    context.setdefault("priority", row.priority or "normal")
                    context.setdefault("category", row.category or "operational")
            finally:
                db.close()

        if recipient_type == "admin" and recipient_id and (not email or not phone):
            db = SessionLocal()
            try:
                staff_email, staff_phone = self._staff_contact(db, recipient_id)
                email = email or staff_email
                phone = phone or staff_phone
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
                    context.setdefault("priority", row.priority or "normal")
            for next_channel in chain:
                address = phone if next_channel == "sms" else email if next_channel == "email" else None
                if not address:
                    continue
                fb_priority = str(context.get("priority") or "normal")
                if not prefs.is_enabled(
                    db,
                    user_role=recipient_type or "customer",
                    user_id=recipient_id or "unknown",
                    category=category,
                    channel=next_channel,
                    priority=fb_priority,
                ):
                    continue
                if quiet.should_mute_channel(
                    db,
                    user_role=recipient_type or "customer",
                    user_id=recipient_id or "unknown",
                    channel=next_channel,
                    priority=fb_priority,
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
                    priority=fb_priority,
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

    def _mark_sent(self, db, notification_id: str) -> None:
        row = db.get(NotificationRecord, notification_id)
        if not row:
            return
        now = datetime.now(UTC)
        row.status = "delivered" if row.channel == "push" else "sent"
        row.sent_at = row.sent_at or now
        if row.channel == "email":  # provider accepted; delivered/opened arrive by webhook
            row.provider_message_id, row.delivery_status = row.provider_message_id or row.id, "accepted"
        else:
            row.delivered_at = now
        db.flush()
        from porterchain_shared.events.catalog import DomainEventType

        # Audit only — publishing notification.sent flooded Redis with no handlers.
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
            publish=False,
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

    def _mark_deferred(self, notification_id: str, reason: str) -> None:
        db = SessionLocal()
        try:
            row = db.get(NotificationRecord, notification_id)
            if not row:
                return
            row.status = "deferred"
            row.failure_reason = reason
            row.next_retry_at = None
            db.commit()
        finally:
            db.close()

    def _send_email(self, recipient: str, template: str, context: dict[str, Any]) -> None:
        if not recipient:
            raise ValueError("email_recipient_required")
        from porterchain_api.db import SessionLocal
        from porterchain_api.notification_engine.bounce import address_is_bounced

        bounce_db = SessionLocal()
        try:
            if address_is_bounced(bounce_db, recipient):
                raise DeliveryDeferred("email_bounced")
        finally:
            bounce_db.close()
        settings = get_platform_settings()
        subject, text_body, html_body = render_email(template, context)
        if context.get("is_sandbox") is True:
            if not subject.upper().startswith("[TEST]"):
                subject = f"[TEST] {subject}"
            text_body = f"[TEST / sandbox — not live capacity]\n\n{text_body}"
        if not settings.smtp_host and not settings.smtp_password:
            raise DeliveryDeferred("email_log_only")
        from_addr = settings.smtp_from_for(context.get("from_alias") or context.get("mail_from"))
        from_name = context.get("from_name") or settings.smtp_from_name or "PorterChain"
        if context.get("is_sandbox") is True and from_name and "TEST" not in from_name.upper():
            from_name = f"{from_name} (TEST)"

        from porterchain_api.notification_engine.unsubscribe import (
            list_unsubscribe_headers,
        )

        extra_headers = list_unsubscribe_headers(settings, context)

        transport = settings.resolve_mail_transport()
        if transport == "https":
            self._send_email_zeptomail_https(
                recipient=recipient,
                subject=subject,
                text_body=text_body,
                html_body=html_body,
                from_addr=from_addr,
                from_name=from_name,
                settings=settings,
                headers=extra_headers,
                reference=context.get("notification_id"),
                reply_to=context.get("reply_to_email"),
            )
            return

        if not settings.smtp_host:
            logger.info("email (log-only): to=%s template=%s", recipient, template)
            return
        self._send_email_smtp(
            recipient=recipient,
            subject=subject,
            text_body=text_body,
            html_body=html_body,
            from_addr=from_addr,
            from_name=from_name,
            settings=settings,
            headers={**extra_headers, **({"Reply-To": context["reply_to_email"]} if context.get("reply_to_email") else {})},
        )

    def _send_email_zeptomail_https(self, **kwargs: Any) -> None:
        """ZeptoMail Send Mail HTTP API (DigitalOcean blocks outbound SMTP)."""
        from porterchain_api.notification_engine.zeptomail import send_zeptomail

        send_zeptomail(**kwargs)

    def _send_email_smtp(
        self,
        *,
        recipient: str,
        subject: str,
        text_body: str,
        html_body: str,
        from_addr: str,
        from_name: str,
        settings: Any,
        headers: dict[str, str] | None = None,
    ) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        for name, value in (headers or {}).items():
            msg[name] = value
        msg["From"] = f"{from_name} <{from_addr}>" if from_name else from_addr
        msg["To"] = recipient
        msg.set_content(text_body)
        msg.add_alternative(html_body, subtype="html")

        host = settings.smtp_host
        port = int(settings.smtp_port or 587)
        # Local stack: always use Mailpit so payment/invoice receipts are inspectable
        # without sending through production SMTP (ZeptoMail).
        if str(getattr(settings, "app_env", "")).lower() in {"local", "development", "dev"}:
            host, port = "localhost", 1025

        # Prod SMTP (when unblocked): 587 + STARTTLS or 465 + SSL. Mailpit: plain 1025.
        tls_ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=tls_ctx) as smtp:
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        elif port == 587:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                smtp.starttls(context=tls_ctx)
                if settings.smtp_user:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as smtp:
                if settings.smtp_user and port != 1025:
                    smtp.login(settings.smtp_user, settings.smtp_password)
                smtp.send_message(msg)

    def _send_sms(self, recipient: str, template: str, context: dict[str, Any]) -> None:
        if not recipient:
            raise ValueError("sms_recipient_required")
        settings = get_platform_settings()
        _, body = render_template(template, context)
        if context.get("is_sandbox") is True:
            body = f"[TEST] {body}"
        if not getattr(settings, "sms_enabled", False):
            logger.info(
                "sms (disabled — set PORTERCHAIN_SMS_ENABLED): to=%s template=%s body=%s",
                recipient,
                template,
                body[:160],
            )
            raise DeliveryDeferred("sms_disabled")
        provider = (getattr(settings, "sms_provider", "") or "").strip().lower()
        if not provider:
            logger.info("sms (log-only, no provider): to=%s template=%s body=%s", recipient, template, body[:160])
            raise DeliveryDeferred("sms_provider_missing")
        if provider == "twilio":
            self._send_sms_twilio(recipient, body, settings)
            return
        raise ValueError(f"sms_provider_not_configured:{provider}")

    def _send_sms_twilio(self, recipient: str, body: str, settings: Any) -> None:
        sid = (getattr(settings, "twilio_account_sid", "") or "").strip()
        token = (getattr(settings, "twilio_auth_token", "") or "").strip()
        from_number = (getattr(settings, "twilio_from_number", "") or "").strip()
        if not sid or not token or not from_number:
            raise DeliveryDeferred("twilio_credentials_missing")
        import httpx

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        resp = httpx.post(
            url,
            data={"To": recipient, "From": from_number, "Body": body[:1500]},
            auth=(sid, token),
            timeout=30.0,
        )
        if resp.status_code >= 400:
            raise ValueError(f"twilio_http_{resp.status_code}:{resp.text[:200]}")

    def _staff_contact(self, db, recipient_id: str) -> tuple[str | None, str | None]:
        """Return (email, phone) for admin fallback when push cannot reach a device.

        Phone: AdminUser.phone first, then linked PorterchainUser.phone.
        """
        if not recipient_id:
            return None, None
        from porterchain_api.admin_models import AdminUser
        from porterchain_api.user_models import PorterchainUser

        user = db.get(AdminUser, recipient_id)
        if not user:
            return None, None
        email = user.email or None
        phone = user.phone or None
        if (not phone or not email) and user.porterchain_user_id:
            pc = db.get(PorterchainUser, user.porterchain_user_id)
            if pc:
                phone = phone or pc.phone
                email = email or pc.email
        return email, phone

    def _send_push(
        self,
        token: str,
        template: str,
        context: dict[str, Any],
        *,
        recipient_type: str,
        recipient_id: str,
    ) -> None:
        from porterchain_api.notification_engine.fcm_service import (
            firebase_credentials_configured,
            resolve_channel_id,
        )

        settings = get_platform_settings()
        priority = str(context.get("priority") or "normal")
        category = str(context.get("category") or "operational")
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
        channel_id = resolve_channel_id(priority=priority, category=category)
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
                # Jeff Dean: critical/high staff must fail closed via email, not silent loss.
                if recipient_type == "admin" and priority in ("critical", "high"):
                    email, phone = self._staff_contact(db, recipient_id)
                    enriched = {
                        **context,
                        "priority": priority,
                        "category": category,
                        "email": email or context.get("email"),
                        "contact_email": email or context.get("contact_email"),
                        "phone": phone or context.get("phone"),
                        "contact_phone": phone or context.get("contact_phone"),
                    }
                    self._try_channel_fallback(
                        {
                            "channel": "push",
                            "template": template,
                            "notification_id": context.get("notification_id"),
                            "recipient_type": recipient_type,
                            "recipient_id": recipient_id,
                            "context": enriched,
                        },
                        failed_channel="push",
                    )
                    raise ValueError("push_token_required_fallback_queued")
                raise ValueError("push_token_required")

            failures = 0
            for t in tokens:
                ok, err, invalid = fcm.send(
                    t,
                    title=str(title),
                    body=str(body),
                    data={k: str(v) for k, v in context.items() if v is not None},
                    deep_link=deep_link,
                    priority=priority,
                    category=category,
                    channel_id=channel_id,
                    template_key=template,
                )
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
