"""Admin notification center service."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

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
        from porterchain_api.notification_engine.user_settings import UserSettingsService

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
        from porterchain_api.admin_models import Claim, SupportTicket
        from porterchain_api.models import Order, OrderException

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
            open_support = (
                db.query(func.count(SupportTicket.id))
                .filter(
                    SupportTicket.merchant_id == entity_id,
                    SupportTicket.status.in_(("open", "in_progress", "waiting")),
                )
                .scalar()
                or 0
            )
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
            open_claims = (
                db.query(func.count(Claim.id))
                .join(Order, Order.id == Claim.order_id)
                .filter(
                    Order.assigned_driver_id == entity_id,
                    Claim.status.in_(("open", "investigating", "pending")),
                )
                .scalar()
                or 0
            )
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
            open_support = (
                db.query(func.count(SupportTicket.id))
                .filter(
                    SupportTicket.customer_id == entity_id,
                    SupportTicket.status.in_(("open", "in_progress", "waiting")),
                )
                .scalar()
                or 0
            )
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
        row = db.get(NotificationRecord, notification_id)
        if not row or row.status not in ("failed", "dead_letter"):
            return False
        row.status = "queued"
        row.next_retry_at = None
        row.failure_reason = None
        db.flush()
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_shared.events.catalog import DomainEventType

        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="notification",
            aggregate_id=row.id,
            payload={
                "notification_id": row.id,
                "channel": row.channel,
                "template": row.template_key,
                "recipient_type": row.recipient_type,
                "recipient_id": row.recipient_id,
                "recipient": row.recipient_address or "",
                "context": {**row.context, "title": row.title, "body": row.body, "deep_link": row.deep_link},
            },
        )
        db.commit()
        return True

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
        }
        if channel in ("email", "sms") and not recipient_address:
            raise ValueError("recipient_address_required")
        from uuid import uuid4

        rec = get_notification_engine().dispatch(
            db,
            event_type="admin.send_test",
            template_key=template_key,
            channel=channel,
            recipient_type=recipient_type,
            recipient_id=recipient_id,
            recipient_address=recipient_address,
            context=ctx,
            priority="normal",
            correlation_id=f"send-test-{uuid4().hex[:12]}",
        )
        # Dev convenience: deliver email/SMS immediately for send-test (Mailpit).
        if rec and channel in ("email", "sms") and recipient_address:
            from porterchain_api.notification_engine.delivery_service import DeliveryService

            DeliveryService().deliver(
                {
                    "notification_id": rec.id,
                    "channel": channel,
                    "template": template_key,
                    "recipient_type": recipient_type,
                    "recipient_id": recipient_id,
                    "recipient": recipient_address,
                    "context": {**ctx, "title": rec.title, "body": rec.body},
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
