"""Resolve the driver's next actionable stop from location + remaining route."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from porterchain_driver.route_optimizer import _coords, _haversine_m
from porterchain_driver.route_optimizer import _coords, _haversine_m
from porterchain_driver.stops import StopsService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

_ACTIONABLE_SKIP = frozenset({"picked_up", "delivered", "pod_completed", "completed", "locked"})


def _is_actionable(stop: Any) -> bool:
    return str(stop.status).lower() not in _ACTIONABLE_SKIP


class NextStopResolver:
    def resolve(self, db: Session, driver: Any) -> dict[str, Any] | None:
        stops_svc = StopsService()
        route = stops_svc.assigned_route(db, driver)
        if not route or not route.stops:
            return None

        actionable = [
            s for s in sorted(route.stops, key=lambda x: x.sequence) if _is_actionable(s)
        ]
        if not actionable:
            return None

        origin = self._driver_origin(db, driver.id, route.stops)
        if origin is None:
            best = actionable[0]
            return self._to_dict(best, distance_m=None)

        best = min(
            actionable,
            key=lambda s: _haversine_m(origin, self._stop_coords(s) or origin),
        )
        dist = _haversine_m(origin, self._stop_coords(best) or origin)
        return self._to_dict(best, distance_m=dist)

    def _driver_origin(
        self, db: Session, driver_id: str, stops: list[Any]
    ) -> tuple[float, float] | None:
        from porterchain_api.driver_models import DriverLocationPing

        ping = (
            db.query(DriverLocationPing)
            .filter(DriverLocationPing.driver_id == driver_id)
            .order_by(DriverLocationPing.created_at.desc())
            .first()
        )
        if ping:
            return float(ping.lat), float(ping.lng)

        for stop in reversed(sorted(stops, key=lambda s: s.sequence)):
            if stop.status in ("picked_up", "delivered", "pod_completed", "completed"):
                coords = self._stop_coords(stop)
                if coords:
                    return coords
        return None

    @staticmethod
    def _stop_coords(stop: Any) -> tuple[float, float] | None:
        addr = stop.address if isinstance(stop.address, dict) else {}
        return _coords(addr)

    @staticmethod
    def _to_dict(stop: Any, *, distance_m: int | None) -> dict[str, Any]:
        addr = stop.address if isinstance(stop.address, dict) else {}
        eta_min = round(distance_m / 500) if distance_m is not None else None
        return {
            "stop_id": stop.stop_id,
            "stop_type": stop.stop_type,
            "order_id": stop.order_id,
            "order_number": stop.order_number,
            "tracking_number": stop.tracking_number,
            "sequence": stop.sequence,
            "address": addr,
            "formatted_address": addr.get("formatted") or addr.get("line1") or "—",
            "distance_m": distance_m,
            "eta_minutes": eta_min,
            "status": stop.status,
        }
