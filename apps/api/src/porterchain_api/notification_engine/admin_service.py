"""Admin notification center — ops board owned by notification_engine.

Dashboard, push-health, queue/history, broadcast/send-test, and entity alert
strips live here so admin_engine does not compose notification SoT.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from porterchain_api.notification_engine.delivery_service import DeliveryService
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.models import (
    NotificationDeliveryLog,
    NotificationDevice,
    NotificationRecord,
)
from porterchain_api.notification_engine.templates import TEMPLATES, template_meta


class NotificationAdminService:
    def dashboard(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(NotificationRecord.id)).scalar() or 0
        queued = db.query(func.count(NotificationRecord.id)).filter(NotificationRecord.status == "queued").scalar() or 0
        failed = (
            db.query(func.count(NotificationRecord.id))
            .filter(NotificationRecord.status.in_(["failed", "dead_letter"]))
            .scalar()
            or 0
        )
        devices = db.query(func.count(NotificationDevice.id)).filter(NotificationDevice.is_active.is_(True)).scalar() or 0
        return {
            "total": total,
            "queued": queued,
            "failed": failed,
            "active_devices": devices,
            "templates": len(TEMPLATES),
        }

    def push_health(self, db: Session) -> dict[str, Any]:
        """Ops Control Tower strip — FCM readiness + staff/driver device reach."""
        from porterchain_shared.config.settings import get_platform_settings

        from porterchain_api.notification_engine.fcm_service import (
            firebase_credentials_configured,
            firebase_production_ready,
            firebase_sdk_available,
        )

        settings = get_platform_settings()
        ready, reason = firebase_production_ready()
        creds_ok = firebase_credentials_configured()
        push_enabled = bool(getattr(settings, "push_enabled", True))
        push_send = bool(getattr(settings, "push_send", True))

        admin_devices = (
            db.query(func.count(NotificationDevice.id))
            .filter(
                NotificationDevice.user_role == "admin",
                NotificationDevice.is_active.is_(True),
            )
            .scalar()
            or 0
        )
        admin_users_with_devices = (
            db.query(func.count(func.distinct(NotificationDevice.user_id)))
            .filter(
                NotificationDevice.user_role == "admin",
                NotificationDevice.is_active.is_(True),
            )
            .scalar()
            or 0
        )
        driver_devices = (
            db.query(func.count(NotificationDevice.id))
            .filter(
                NotificationDevice.user_role == "driver",
                NotificationDevice.is_active.is_(True),
            )
            .scalar()
            or 0
        )

        cutoff = datetime.now(UTC).replace(microsecond=0)
        window_start = cutoff - timedelta(hours=24)
        critical_base = db.query(NotificationRecord).filter(
            NotificationRecord.channel == "push",
            NotificationRecord.priority == "critical",
            NotificationRecord.created_at >= window_start,
        )
        critical_24h = critical_base.count()
        critical_delivered_24h = (
            db.query(func.count(NotificationRecord.id))
            .filter(
                NotificationRecord.channel == "push",
                NotificationRecord.priority == "critical",
                NotificationRecord.created_at >= window_start,
                NotificationRecord.status.in_(("sent", "delivered")),
            )
            .scalar()
            or 0
        )
        critical_failed_24h = (
            db.query(func.count(NotificationRecord.id))
            .filter(
                NotificationRecord.channel == "push",
                NotificationRecord.priority == "critical",
                NotificationRecord.created_at >= window_start,
                NotificationRecord.status.in_(("failed", "dead_letter")),
            )
            .scalar()
            or 0
        )
        last_critical = (
            db.query(NotificationRecord)
            .filter(
                NotificationRecord.channel == "push",
                NotificationRecord.priority.in_(("critical", "high")),
            )
            .order_by(NotificationRecord.created_at.desc())
            .first()
        )

        tone = "ok"
        issues: list[str] = []
        if not push_enabled:
            tone = "warn"
            issues.append("Push disabled (PORTERCHAIN_PUSH_ENABLED)")
        elif not creds_ok:
            tone = "warn" if settings.app_env in ("local", "development", "test") else "danger"
            issues.append(reason or "FCM credentials missing — push is log-only")
        elif not push_send:
            tone = "warn"
            issues.append("Push dry-run (PORTERCHAIN_PUSH_SEND=false)")
        if admin_users_with_devices == 0:
            tone = "danger" if tone != "ok" else "warn"
            issues.append("No admin browsers registered — staff risk alerts email-only")
        if not ready and settings.app_env not in ("local", "development", "test"):
            tone = "danger"
            if reason:
                issues.append(reason)

        return {
            "tone": tone,
            "issues": issues,
            "fcm": {
                "sdk_available": firebase_sdk_available(),
                "credentials_configured": creds_ok,
                "production_ready": ready,
                "production_ready_reason": reason,
                "project_id": getattr(settings, "firebase_project_id", None) or None,
                "push_enabled": push_enabled,
                "push_send": push_send,
                "app_env": settings.app_env,
            },
            "devices": {
                "admin_active": int(admin_devices),
                "admin_users": int(admin_users_with_devices),
                "driver_active": int(driver_devices),
            },
            "critical_24h": {
                "total": int(critical_24h),
                "delivered": int(critical_delivered_24h),
                "failed": int(critical_failed_24h),
            },
            "last_urgent_push": (
                {
                    "id": last_critical.id,
                    "template_key": last_critical.template_key,
                    "priority": last_critical.priority,
                    "status": last_critical.status,
                    "created_at": last_critical.created_at.isoformat() if last_critical.created_at else None,
                }
                if last_critical
                else None
            ),
        }

    def list_records(
        self,
        db: Session,
        *,
        status: str | None = None,
        channel: str | None = None,
        search: str | None = None,
        recipient_type: str | None = None,
        recipient_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        q = db.query(NotificationRecord)
        if status:
            q = q.filter(NotificationRecord.status == status)
        if channel:
            q = q.filter(NotificationRecord.channel == channel)
        if recipient_type:
            q = q.filter(NotificationRecord.recipient_type == recipient_type)
        if recipient_id:
            q = q.filter(NotificationRecord.recipient_id == recipient_id)
        if search:
            like = f"%{search}%"
            q = q.filter(
                or_(
                    NotificationRecord.title.ilike(like),
                    NotificationRecord.recipient_id.ilike(like),
                    NotificationRecord.recipient_address.ilike(like),
                    NotificationRecord.template_key.ilike(like),
                )
            )
        rows = q.order_by(NotificationRecord.created_at.desc()).limit(limit).all()
        return [self._record_dict(r) for r in rows]

    def entity_alerts(
        self,
        db: Session,
        *,
        recipient_type: str,
        recipient_id: str,
        limit: int = 15,
    ) -> dict[str, Any]:
        """Trust strip payload for Merchant / Driver / Customer 360 (Wave 3)."""
        role = recipient_type.strip().lower()
        if role not in ("merchant", "driver", "customer"):
            raise ValueError("invalid_recipient_type")
        entity_id = recipient_id.strip()
        if not entity_id:
            raise ValueError("recipient_id_required")

        from porterchain_api.notification_engine.device_service import DeviceService
        from porterchain_api.notification_engine.preference_service import (
            DEFAULT_CATEGORIES,
            PreferenceService,
            _default_channel_flags,
        )
        from porterchain_api.notification_engine.user_settings import (
            UserSettingsService,
        )

        recent = self.list_records(
            db, recipient_type=role, recipient_id=entity_id, limit=limit
        )

        prefs_svc = PreferenceService()
        existing = {
            p.category: p
            for p in prefs_svc.get_all(db, user_role=role, user_id=entity_id)
        }
        preferences: list[dict[str, Any]] = []
        for category in DEFAULT_CATEGORIES:
            row = existing.get(category)
            if row:
                preferences.append(
                    {
                        "category": row.category,
                        "email_enabled": row.email_enabled,
                        "push_enabled": row.push_enabled,
                        "sms_enabled": row.sms_enabled,
                        "in_app_enabled": row.in_app_enabled,
                        "persisted": True,
                    }
                )
            else:
                flags = _default_channel_flags(category)
                preferences.append(
                    {
                        "category": category,
                        **flags,
                        "persisted": False,
                    }
                )

        settings_svc = UserSettingsService()
        settings_row = settings_svc.get(db, user_role=role, user_id=entity_id)
        tz = settings_svc.resolve_timezone(db, user_role=role, user_id=entity_id)
        settings = settings_svc.to_dict(settings_row, timezone_fallback=tz)

        devices: list[dict[str, Any]] = []
        if role in ("driver", "customer"):
            for d in DeviceService().list_active(db, user_role=role, user_id=entity_id):
                devices.append(
                    {
                        "id": d.id,
                        "platform": d.platform,
                        "device_name": d.device_name,
                        "app_version": d.app_version,
                        "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                        "notification_permission": d.notification_permission,
                    }
                )

        care = self._care_counts(db, role, entity_id)
        muted = [
            p["category"]
            for p in preferences
            if not (p["email_enabled"] or p["push_enabled"] or p["in_app_enabled"] or p["sms_enabled"])
        ]

        return {
            "recipient_type": role,
            "recipient_id": entity_id,
            "recent": recent,
            "preferences": preferences,
            "settings": settings,
            "devices": devices,
            "care": care,
            "muted_categories": muted,
            "links": {
                "notifications_history": "/notifications?tab=history",
                "notifications_devices": "/notifications?tab=devices",
            },
        }

    def _care_counts(self, db: Session, role: str, entity_id: str) -> dict[str, int]:
        from porterchain_api.booking_models import Order, OrderException
        from porterchain_api.notification_engine.care_reads import (
            open_claim_count_for_driver,
            open_ticket_count,
        )

        open_exc = 0
        open_support = 0
        open_claims = 0
        if role == "merchant":
            open_exc = (
                db.query(func.count(OrderException.id))
                .join(Order, Order.id == OrderException.order_id)
                .filter(
                    Order.merchant_id == entity_id,
                    OrderException.status.in_(("open", "acknowledged")),
                )
                .scalar()
                or 0
            )
            open_support = open_ticket_count(db, merchant_id=entity_id)
        elif role == "driver":
            open_exc = (
                db.query(func.count(OrderException.id))
                .join(Order, Order.id == OrderException.order_id)
                .filter(
                    Order.assigned_driver_id == entity_id,
                    OrderException.status.in_(("open", "acknowledged")),
                )
                .scalar()
                or 0
            )
            open_claims = open_claim_count_for_driver(db, entity_id)
        elif role == "customer":
            open_exc = (
                db.query(func.count(OrderException.id))
                .join(Order, Order.id == OrderException.order_id)
                .filter(
                    Order.customer_id == entity_id,
                    OrderException.status.in_(("open", "acknowledged")),
                )
                .scalar()
                or 0
            )
            open_support = open_ticket_count(db, customer_id=entity_id)
        return {
            "open_exceptions": int(open_exc),
            "open_support_tickets": int(open_support),
            "open_claims": int(open_claims),
        }

    def list_devices(self, db: Session, *, limit: int = 200) -> list[dict[str, Any]]:
        rows = (
            db.query(NotificationDevice)
            .filter(NotificationDevice.is_active.is_(True))
            .order_by(NotificationDevice.last_seen_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": d.id,
                "user_role": d.user_role,
                "user_id": d.user_id,
                "platform": d.platform,
                "device_name": d.device_name,
                "app_version": d.app_version,
                "os_version": d.os_version,
                "language": d.language,
                "timezone": d.timezone,
                "notification_permission": d.notification_permission,
                "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
                "created_at": d.created_at.isoformat(),
            }
            for d in rows
        ]

    def templates_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "category": template_meta(key).get("category", "operational"),
                "subject": spec.get("subject", ""),
            }
            for key, spec in TEMPLATES.items()
        ]

    def retry(self, db: Session, notification_id: str) -> bool:
        return get_notification_engine().requeue(db, notification_id)

    def broadcast(
        self,
        db: Session,
        *,
        recipient_type: str,
        recipient_id: str,
        title: str,
        body: str,
        channel: str = "in_app",
    ) -> dict[str, Any]:
        rec = get_notification_engine().dispatch(
            db,
            event_type="admin.broadcast",
            template_key="system_alert",
            channel=channel,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            context={"message": body, "title": title, "body": body},
            priority="normal",
        )
        db.commit()
        return {"ok": True, "notification_id": rec.id if rec else None}

    def send_test(
        self,
        db: Session,
        *,
        template_key: str,
        channel: str,
        recipient_type: str,
        recipient_id: str,
        recipient_address: str | None = None,
    ) -> dict[str, Any]:
        if template_key not in TEMPLATES:
            raise LookupError("template_not_found")
        ctx = {
            "tracking_number": "TRK-TEST-001",
            "order_number": "ORD-TEST-001",
            "quote_id": "Q-TEST-001",
            "amount_display": "$0.00",
            "invoice_number": "INV-TEST-001",
            "merchant_name": "Test Merchant",
            "message": "PorterChain notification send-test",
            "title": "Send test",
            "body": "PorterChain notification send-test",
            "exception_type": "test",
            "claim_number": "CLM-TEST",
            "claim_type": "general",
            "ticket_number": "TKT-TEST",
            "subject": "Send test",
            "status": "open",
            "celsius": "0",
            "route_id": "RTE-TEST",
            "stops_count": "1",
            "recovery_url": "https://porterchain.com",
            "reset_url": "https://porterchain.com",
            "activate_url": "https://porterchain.com",
            "code": "000000",
            "receipt_number": "RCP-TEST",
            "receipt_url": "https://porterchain.com",
            "priority": "high" if channel == "push" else "normal",
            "category": "orders" if channel == "push" else "operational",
        }
        if channel in ("email", "sms") and not recipient_address:
            raise ValueError("recipient_address_required")

        test_priority = "high" if channel == "push" else "normal"
        rec = get_notification_engine().dispatch(
            db,
            event_type="admin.send_test",
            template_key=template_key,
            channel=channel,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            recipient_address=recipient_address,
            context=ctx,
            priority=test_priority,
            correlation_id=f"send-test-{uuid4().hex[:12]}",
        )
        # Dev convenience: deliver email/SMS/push immediately for send-test (Mailpit / FCM).
        if rec and channel in ("email", "sms") and recipient_address:
            DeliveryService().deliver(
                {
                    "notification_id": rec.id,
                    "channel": channel,
                    "template": template_key,
                    "recipient_type": recipient_type,
                    "recipient_id": recipient_id,
                    "recipient": recipient_address,
                    "context": {
                        **ctx,
                        "title": rec.title,
                        "body": rec.body,
                        "priority": test_priority,
                    },
                }
            )
        elif rec and channel == "push":
            DeliveryService().deliver(
                {
                    "notification_id": rec.id,
                    "channel": channel,
                    "template": template_key,
                    "recipient_type": recipient_type,
                    "recipient_id": recipient_id,
                    "recipient": "",
                    "context": {
                        **ctx,
                        "title": rec.title,
                        "body": rec.body,
                        "priority": test_priority,
                        "category": "orders",
                    },
                }
            )
        db.commit()
        return {
            "ok": True,
            "notification_id": rec.id if rec else None,
            "status": rec.status if rec else "suppressed",
            "template_key": template_key,
            "channel": channel,
        }

    def delivery_logs(self, db: Session, notification_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        rows = (
            db.query(NotificationDeliveryLog)
            .filter(NotificationDeliveryLog.notification_id == notification_id)
            .order_by(NotificationDeliveryLog.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "notification_id": r.notification_id,
                "channel": r.channel,
                "template": r.template,
                "recipient": r.recipient,
                "status": r.status,
                "error": r.error,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def _record_dict(self, r: NotificationRecord) -> dict[str, Any]:
        return {
            "id": r.id,
            "event_type": r.event_type,
            "template_key": r.template_key,
            "category": r.category,
            "channel": r.channel,
            "priority": r.priority,
            "recipient_type": r.recipient_type,
            "recipient_id": r.recipient_id,
            "recipient_address": r.recipient_address,
            "title": r.title,
            "body": r.body,
            "status": r.status,
            "retry_count": r.retry_count,
            "failure_reason": r.failure_reason,
            "search_tags": r.search_tags,
            "is_read": r.is_read,
            "queued_at": r.queued_at.isoformat() if r.queued_at else None,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "delivered_at": r.delivered_at.isoformat() if r.delivered_at else None,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "clicked_at": r.clicked_at.isoformat() if r.clicked_at else None,
            "created_at": r.created_at.isoformat(),
        }
