"""Package events: merchant_engine may raise them without importing booking_engine."""

from __future__ import annotations

from sqlalchemy.orm import Session

INCIDENT_REPORTED = "incident.reported"


def emit_package_missing(
    db: Session,
    *,
    order_id: str,
    driver_id: str | None,
    exception_id: str,
    package_id: str,
    reason: str,
) -> None:
    """A box was not at pickup: same `incident.reported` event as a stop exception (ops alert)."""
    from porterchain_api.booking_engine._core import emit_event

    emit_event(
        db,
        event_type=INCIDENT_REPORTED,
        aggregate_type="order",
        aggregate_id=order_id,
        actor_type="driver",
        actor_id=driver_id,
        payload={
            "order_id": order_id,
            "driver_id": driver_id,
            "exception_type": "package_missing",
            "exception_id": exception_id,
            "package_id": package_id,
            "reason": reason,
        },
    )
