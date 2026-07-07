"""Emergency button — immediate ops alert."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class EmergencyService:
    def trigger(
        self,
        db: Session,
        driver: Any,
        *,
        location: dict | None = None,
        message: str | None = None,
    ) -> dict:
        from porterchain_driver.support import SupportService
        from porterchain_api.booking_engine._core import emit_event
        from porterchain_api.driver_models import DriverLocationPing
        from datetime import UTC, datetime

        if location:
            db.add(
                DriverLocationPing(
                    driver_id=driver.id,
                    lat=location.get("lat", 0),
                    lng=location.get("lng", 0),
                    accuracy_m=location.get("accuracy"),
                    source="emergency",
                )
            )

        ticket = SupportService().create_ticket(
            db,
            driver,
            subject="EMERGENCY — Driver distress signal",
            description=message or "Driver activated SOS / emergency button",
            priority="critical",
            category="driver_support",
        )
        emit_event(
            db,
            event_type="driver.emergency",
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="driver",
            actor_id=driver.id,
            payload={"location": location, "ticket_id": ticket["id"], "driver_id": driver.id},
        )
        from porterchain_driver.communications import DriverCommunicationService

        DriverCommunicationService().notify_driver(
            db,
            driver,
            title="Emergency alert sent",
            body="Operations has been notified of your SOS.",
            template="driver_alert",
            category="security",
            priority="critical",
        )
        db.flush()
        return {"status": "alert_sent", "ticket_id": ticket["id"], "ops_notified": True}
