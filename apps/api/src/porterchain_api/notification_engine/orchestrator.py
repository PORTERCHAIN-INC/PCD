"""Notification orchestration — delegates to NotificationEngine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.engine import get_notification_engine


class NotificationOrchestrator:
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
        customer_id: str | None = None,
    ) -> None:
        engine = get_notification_engine()
        ctx = {
            "tracking_number": tracking_number,
            "order_number": order_number,
            "invoice_number": invoice_number,
            "booking_number": booking_number,
        }
        recipient_id = customer_id or correlation_id
        engine.dispatch(
            db,
            event_type="booking.confirmed",
            template_key="booking_confirmed",
            channel="email",
            recipient_type="customer",
            recipient_id=recipient_id,
            recipient_address=email,
            context=ctx,
            correlation_id=correlation_id,
            search_tags=ctx,
        )
        if phone:
            engine.dispatch(
                db,
                event_type="booking.confirmed",
                template_key="booking_confirmed",
                channel="sms",
                recipient_type="customer",
                recipient_id=recipient_id,
                recipient_address=phone,
                context=ctx,
                correlation_id=correlation_id,
            )
        engine.dispatch(
            db,
            event_type="booking.confirmed",
            template_key="booking_confirmed",
            channel="in_app",
            recipient_type="customer",
            recipient_id=recipient_id,
            context=ctx,
            correlation_id=correlation_id,
        )

    def send_checkout_recovery(self, db: Session, *, email: str, quote_id: str, recovery_url: str) -> None:
        engine = get_notification_engine()
        ctx = {"quote_id": quote_id, "recovery_url": recovery_url}
        engine.dispatch(
            db,
            event_type="checkout.abandoned",
            template_key="checkout_recovery",
            channel="email",
            recipient_type="customer",
            recipient_id=quote_id,
            recipient_address=email,
            context=ctx,
            correlation_id=quote_id,
        )
