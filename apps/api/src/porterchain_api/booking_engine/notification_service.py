"""Notification service — email and push per BUSINESS_WORKFLOW.md."""

import logging

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.orchestrator import NotificationOrchestrator

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self) -> None:
        self._orchestrator = NotificationOrchestrator()

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
        try:
            self._orchestrator.send_booking_confirmation(
                db,
                email=email,
                phone=phone,
                tracking_number=tracking_number,
                order_number=order_number,
                invoice_number=invoice_number,
                booking_number=booking_number,
                correlation_id=correlation_id,
            )
        except Exception as exc:
            logger.warning("notification queue failed: %s", exc)

    def send_checkout_recovery(self, db: Session, *, email: str, quote_id: str, recovery_url: str) -> None:
        try:
            self._orchestrator.send_checkout_recovery(
                db, email=email, quote_id=quote_id, recovery_url=recovery_url
            )
        except Exception as exc:
            logger.warning("recovery notification failed: %s", exc)
