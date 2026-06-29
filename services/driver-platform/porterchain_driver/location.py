"""Driver location pings — Porterchain + Fleetbase sync."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


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
        fleetbase_bridge: Any = None,
    ) -> dict:
        from porterchain_api.driver_models import DriverLocationPing

        ping = DriverLocationPing(
            driver_id=driver.id,
            lat=lat,
            lng=lng,
            accuracy_m=accuracy_m,
            heading=heading,
            speed_mps=speed_mps,
            source="app",
        )
        db.add(ping)
        if fleetbase_bridge and driver.fleetbase_driver_id:
            fleetbase_bridge.track_driver_location(
                driver.fleetbase_driver_id,
                lat=lat,
                lng=lng,
                heading=heading,
                speed=speed_mps,
            )
        db.flush()
        return {"recorded": True, "ping_id": ping.id}
