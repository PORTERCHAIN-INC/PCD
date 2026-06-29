"""Notification event handlers — react to domain events, queue outbound messages."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)


def _queue_notification(
    *,
    channel: str,
    template: str,
    recipient: dict[str, str],
    context: dict[str, Any],
    correlation_id: str | None,
) -> None:
    from porterchain_api.booking_engine._core import emit_event
    from porterchain_api.db import SessionLocal

    db = SessionLocal()
    try:
        emit_event(
            db,
            event_type=DomainEventType.NOTIFICATION_QUEUED,
            aggregate_type="notification",
            aggregate_id=correlation_id or "system",
            correlation_id=correlation_id,
            payload={
                "channel": channel,
                "template": template,
                "recipient": recipient,
                "context": context,
            },
        )
        db.commit()
    finally:
        db.close()


def notify_order_booked(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    email = payload.get("email")
    if not email:
        return
    _queue_notification(
        channel="email",
        template="order_booked",
        recipient={"email": email, "phone": payload.get("phone", "")},
        context={
            "tracking_number": payload.get("tracking_number"),
            "order_number": payload.get("order_number"),
        },
        correlation_id=envelope.get("aggregate_id"),
    )


def notify_booking_confirmed(envelope: dict[str, Any]) -> None:
    payload = envelope.get("payload", {})
    email = payload.get("email")
    if not email:
        return
    from porterchain_api.booking_engine.notification_service import NotificationService
    from porterchain_api.db import SessionLocal

    db = SessionLocal()
    try:
        NotificationService().send_booking_confirmation(
            db,
            email=email,
            phone=payload.get("phone"),
            tracking_number=payload.get("tracking_number", ""),
            order_number=payload.get("order_number", ""),
            invoice_number=payload.get("invoice_number", ""),
            booking_number=payload.get("booking_number", ""),
            correlation_id=envelope.get("aggregate_id"),
        )
        db.commit()
    finally:
        db.close()
