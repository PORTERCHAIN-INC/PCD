"""Navigation — route polyline and turn-by-turn metadata via Fleetbase."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class NavigationService:
    def route_for_order(self, db: Session, driver: Any, order_id: str, *, fleetbase_bridge: Any = None) -> dict:
        from porterchain_api.models import Order

        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.assigned_driver_id == driver.id)
            .first()
        )
        if not order:
            raise LookupError("order_not_found")

        route_polyline = None
        eta_seconds = None
        distance_meters = None

        if fleetbase_bridge and order.fleetbase_order_id:
            route_data = fleetbase_bridge.fetch_route(order.fleetbase_order_id)
            if route_data:
                route_polyline = route_data.get("polyline") or route_data.get("route_polyline")
                eta_seconds = route_data.get("eta_seconds") or route_data.get("duration")
                distance_meters = route_data.get("distance_meters") or route_data.get("distance")

        return {
            "order_id": order.id,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "route_polyline": route_polyline,
            "eta_seconds": eta_seconds,
            "distance_meters": distance_meters,
            "navigation_url": _maps_url(order.pickup, order.dropoff),
        }

    def route_for_stops(self, db: Session, driver: Any, route_id: str, *, fleetbase_bridge: Any = None) -> dict:
        from porterchain_driver.stops import StopsService

        stops = StopsService().stops_for_route(db, driver.id, route_id)
        polylines = []
        for stop in stops:
            order_id = stop.order_id
            try:
                nav = self.route_for_order(db, driver, order_id, fleetbase_bridge=fleetbase_bridge)
                if nav.get("route_polyline"):
                    polylines.append(nav["route_polyline"])
            except LookupError:
                continue
        return {
            "route_id": route_id,
            "stops": [
                {
                    "stop_id": s.stop_id,
                    "stop_type": s.stop_type,
                    "address": s.address,
                    "sequence": s.sequence,
                }
                for s in stops
            ],
            "route_polyline": polylines[0] if polylines else None,
        }


def _maps_url(pickup: dict, dropoff: dict) -> str | None:
    plat, plng = pickup.get("lat"), pickup.get("lng")
    dlat, dlng = dropoff.get("lat"), dropoff.get("lng")
    if None in (plat, plng, dlat, dlng):
        return None
    return f"https://www.google.com/maps/dir/?api=1&origin={plat},{plng}&destination={dlat},{dlng}&travelmode=driving"
