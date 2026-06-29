"""Notification service — email and push per BUSINESS_WORKFLOW.md."""

import logging

from porterchain_api.booking_engine import events as E
from porterchain_api.booking_engine._core import emit_event
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificationService:
    def send_booking_confirmation(
        self,
        db: Session,
        *,
        email: str,
        phone: str | None,
        tracking_number: str,
        order_number: str,
        invoice_number: str,
        booking_number: str,
        correlation_id: str,
    ) -> None:
        context = {
            "tracking_number": tracking_number,
            "order_number": order_number,
            "invoice_number": invoice_number,
            "booking_number": booking_number,
        }
        try:
            from porterchain_services.notifications.service import NotificationService as InfraNotification

            infra = InfraNotification()
            infra.send_booking_confirmed(email, phone or "", tracking_number)
        except Exception as exc:
            logger.warning("notification queue failed: %s", exc)

        emit_event(
            db,
            event_type=E.NOTIFICATION_SENT,
            aggregate_type="notification",
            aggregate_id=correlation_id,
            correlation_id=correlation_id,
            payload={"channel": "email", "template": "booking_confirmed", **context},
        )
        if phone:
            emit_event(
                db,
                event_type=E.NOTIFICATION_SENT,
                aggregate_type="notification",
                aggregate_id=correlation_id,
                correlation_id=correlation_id,
                payload={"channel": "sms", "template": "booking_confirmed", "phone": phone},
            )
        db.commit()

    def send_checkout_recovery(self, db: Session, *, email: str, quote_id: str, recovery_url: str) -> None:
        try:
            from porterchain_services.notifications.service import NotificationService as InfraNotification

            InfraNotification().send_checkout_recovery(email, quote_id, recovery_url)
        except Exception as exc:
            logger.warning("recovery notification failed: %s", exc)
        emit_event(
            db,
            event_type=E.NOTIFICATION_SENT,
            aggregate_type="notification",
            aggregate_id=quote_id,
            payload={"channel": "email", "template": "checkout_recovery"},
        )
        db.commit()
