"""Driver location pings — last-known Redis + Fleetbase enqueue.

``driver_location_pings`` INSERT is off unless ``write_ping_table`` (GPS_WRITE_PING_TABLE).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _parse_stamp(recorded_at: str | None) -> datetime:
    if recorded_at:
        try:
            parsed = datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.astimezone(UTC)
        except (TypeError, ValueError):
            pass
    return datetime.now(UTC)


def _active_shift_id(db: Session, driver_id: str) -> str | None:
    from porterchain_api.driver_models import DriverShift

    row = (
        db.query(DriverShift)
        .filter(DriverShift.driver_id == driver_id, DriverShift.ended_at.is_(None))
        .order_by(DriverShift.started_at.desc())
        .first()
    )
    return row.id if row else None


class LocationService:
    def record_ping(
        self,
        db: Session,
        driver: Any,
        *,
        lat: float,
        lng: float,
        accuracy_m: float | None = None,
        heading: float | None = None,
        speed_mps: float | None = None,
        recorded_at: str | None = None,
        write_ping_table: bool = False,
        fleetbase_bridge: Any = None,
    ) -> dict:
        from porterchain_api.driver_engine.last_known import (
            accumulate_shift_mileage,
            write_last_known,
        )

        stamp = _parse_stamp(recorded_at)
        ping_id: str | None = None
        if write_ping_table:
            from porterchain_api.driver_models import DriverLocationPing

            ping = DriverLocationPing(
                driver_id=driver.id,
                lat=lat,
                lng=lng,
                accuracy_m=accuracy_m,
                heading=heading,
                speed_mps=speed_mps,
                source="app",
                created_at=stamp,
            )
            db.add(ping)
            db.flush()
            ping_id = ping.id
        try:
            write_last_known(
                driver_id=driver.id,
                lat=lat,
                lng=lng,
                recorded_at=stamp,
                accuracy_m=accuracy_m,
                heading=heading,
                speed_mps=speed_mps,
                fleetbase_driver_id=getattr(driver, "fleetbase_driver_id", None),
            )
            shift_id = _active_shift_id(db, driver.id)
            if shift_id:
                accumulate_shift_mileage(
                    driver_id=driver.id,
                    shift_id=shift_id,
                    lat=lat,
                    lng=lng,
                    recorded_at=stamp,
                )
        except Exception:
            logger.debug("gps last-known write skipped driver=%s", driver.id, exc_info=True)
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.track_driver_location(
                db,
                driver_id=driver.id,
                fleetbase_driver_id=driver.fleetbase_driver_id,
                lat=lat,
                lng=lng,
                heading=heading,
                speed=speed_mps,
                recorded_at=stamp.isoformat(),
            )
        db.flush()
        return {"recorded": True, "ping_id": ping_id, "recorded_at": stamp.isoformat()}
