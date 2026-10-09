"""Notification orchestration — delegates to NotificationEngine."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.notification_engine.engine import get_notification_engine


class NotificationOrchestrator:

    def send_consignee_tracking(
        self,
        db: Session,
        *,
        email: str,
        tracking_number: str,
        order_number: str,
        public_track_url: str,
        merchant_name: str,
        correlation_id: str,
    ) -> None:
        engine = get_notification_engine()
        ctx = {
            "tracking_number": tracking_number,
            "order_number": order_number,
            "public_track_url": public_track_url,
            "merchant_name": merchant_name,
        }
        engine.dispatch(
            db,
            event_type="consignee.tracking",
            template_key="consignee_tracking",
            channel="email",
            recipient_type="consignee",
            recipient_id=correlation_id,
            recipient_address=email,
            context=ctx,
            correlation_id=correlation_id,
            search_tags=ctx,
            category="tracking",
        )
