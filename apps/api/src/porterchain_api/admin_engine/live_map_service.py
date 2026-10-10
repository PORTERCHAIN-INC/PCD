"""Live map snapshot — Redis last_known pins + PorterChain order stops.

Policy: the browser gets Google tiles only. Driver pins come from
``dispatch_engine.gps_board`` (on-duty shift + Redis last_known). Order stop
markers come from the PorterChain order. Route geometry is computed by
MapsService (Valhalla); without it we fall back to straight legs between
stops, labeled source="direct".
"""

from __future__ import annotations

import logging
from typing import Any

from porterchain_services.maps.polyline import decode_polyline
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import _coords
from porterchain_api.admin_models import Driver
from porterchain_api.booking_models import Order
from porterchain_api.dispatch_engine import gps_board

logger = logging.getLogger(__name__)

ACTIVE_LIMIT = 200
# Square 0.01° grid is the no-h3 fallback only. Primary density is H3 res 8.
DENSITY_CELL = 0.01


def _density_cells(orders: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], str]:
    from porterchain_api.spatial.h3_index import DENSITY_RESOLUTION as H3_DENSITY_RES
    from porterchain_api.spatial.h3_index import cell as h3_cell
    from porterchain_api.spatial.h3_index import cell_center

    buckets: dict[str, dict[str, Any]] = {}
    fallback: dict[tuple[int, int], dict[str, Any]] = {}
    for o in orders:
        for s in o.get("stops") or []:
            try:
                lat = float(s["lat"])
                lng = float(s["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            hex_id = h3_cell(lat, lng, res=H3_DENSITY_RES)
            if hex_id:
                cell = buckets.get(hex_id)
                if cell is None:
                    center = cell_center(hex_id) or (lat, lng)
                    buckets[hex_id] = {
                        "lat": center[0],
                        "lng": center[1],
                        "weight": 1,
                    }
                else:
                    cell["weight"] += 1
                continue
            key = (int(lat / DENSITY_CELL), int(lng / DENSITY_CELL))
            cell = fallback.get(key)
            if cell is None:
                fallback[key] = {
                    "lat": (key[0] + 0.5) * DENSITY_CELL,
                    "lng": (key[1] + 0.5) * DENSITY_CELL,
                    "weight": 1,
                }
            else:
                cell["weight"] += 1
    values = list(buckets.values()) or list(fallback.values())
    source = "h3" if buckets else "grid"
    return sorted(values, key=lambda c: -c["weight"]), source


def _stop_label(raw: dict, fallback: str) -> str:
    for key in ("formatted", "address", "formatted_address", "city", "name"):
        value = raw.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return fallback


def order_stop_points(order: Order) -> list[dict[str, Any]]:
    """Ordered map points for an order: rich stops[] first, legacy fields next."""
    meta = order.compliance_metadata or {}
    raw_stops = meta.get("stops")
    stops: list[dict[str, Any]] = []

    if isinstance(raw_stops, list) and raw_stops:
        ordered = sorted(
            (s for s in raw_stops if isinstance(s, dict)),
            key=lambda s: s.get("sequence", 0),
        )
        for i, s in enumerate(ordered):
            c = _coords(s)
            if not c:
                continue
            stop_type = str(s.get("type") or "").lower()
            kind = (
                "pickup"
                if stop_type == "pickup"
                else "dropoff"
                if stop_type == "dropoff"
                else "stop"
            )
            stops.append(
                {
                    "lat": c[0],
                    "lng": c[1],
                    "kind": kind,
                    "label": _stop_label(s, f"Stop {i + 1}"),
                }
            )
        if stops:
            return stops

    pickup = _coords(order.pickup)
    if pickup:
        stops.append(
            {
                "lat": pickup[0],
                "lng": pickup[1],
                "kind": "pickup",
                "label": _stop_label(order.pickup or {}, "Pickup"),
            }
        )
    for i, s in enumerate(meta.get("additional_stops") or []):
        c = _coords(s if isinstance(s, dict) else None)
        if c:
            stops.append(
                {
                    "lat": c[0],
                    "lng": c[1],
                    "kind": "stop",
                    "label": _stop_label(s, f"Stop {i + 1}"),
                }
            )
    dropoff = _coords(order.dropoff)
    if dropoff:
        stops.append(
            {
                "lat": dropoff[0],
                "lng": dropoff[1],
                "kind": "dropoff",
                "label": _stop_label(order.dropoff or {}, "Delivery"),
            }
        )
    return stops


class LiveMapService:
    def __init__(self, adapter: Any = None, maps: Any = None) -> None:
        del adapter  # leftover GET path inverted — mirror only
        self._maps = maps

    def _get_maps(self) -> Any:
        if self._maps is None:
            from porterchain_services.maps.service import MapsService

            self._maps = MapsService()
        return self._maps

    def snapshot(self, db: Session) -> dict[str, Any]:
        # Lazy: buckets ↔ booking_engine import cycle.
        from porterchain_api.order_engine.buckets import IN_FLIGHT

        orders = (
            db.query(Order)
            .filter(Order.is_sandbox.is_(False), Order.state.in_(IN_FLIGHT))
            .order_by(Order.scheduled_at.asc())
            .limit(ACTIVE_LIMIT)
            .all()
        )
        driver_ids = {o.assigned_driver_id for o in orders if o.assigned_driver_id}
        names = (
            dict(db.query(Driver.id, Driver.full_name).filter(Driver.id.in_(driver_ids)).all())
            if driver_ids
            else {}
        )
        out_orders = []
        for o in orders:
            stops = order_stop_points(o)
            if not stops:
                continue
            out_orders.append(
                {
                    "id": o.id,
                    "tracking_number": o.tracking_number,
                    "state": o.state,
                    "driver": names.get(o.assigned_driver_id) if o.assigned_driver_id else None,
                    "stops": stops,
                }
            )

        drivers_out, drivers_source = gps_board.board_pins(db)

        density, density_source = _density_cells(out_orders)
        return {
            "drivers": drivers_out,
            "orders": out_orders,
            "drivers_source": drivers_source,
            "density": density,
            "density_source": density_source,
        }

    def playback(self, db: Session, order_id: str) -> dict[str, Any]:
        """Shift/order breadcrumb playback. Empty until shift_trace is wired."""
        order = db.get(Order, order_id)
        if not order:
            raise LookupError(f"Order {order_id} not found")

        return {
            "order_id": order_id,
            "points": [],
            "source": "none",
            "message": "No driver GPS yet",
        }

    def route_geometry(self, db: Session, order_id: str) -> dict[str, Any]:
        order = db.get(Order, order_id)
        if not order:
            raise LookupError(f"Order {order_id} not found")

        stops = order_stop_points(order)
        points = [(s["lat"], s["lng"]) for s in stops]
        path: list[list[float]] = [[p[0], p[1]] for p in points]
        source = "direct"
        distance_m: int | None = None
        duration_s: int | None = None

        if len(points) >= 2:
            response = self._get_maps().route_multi(points)
            if response:
                decoded: list[tuple[float, float]] = []
                trip = response.get("trip", {}) if isinstance(response, dict) else {}
                for leg in trip.get("legs", []) or []:
                    decoded.extend(decode_polyline(leg.get("shape") or "", precision=6))
                if decoded:
                    path = [[lat, lng] for lat, lng in decoded]
                    source = "valhalla"
                summary = trip.get("summary", {}) or {}
                if summary.get("length") is not None:
                    distance_m = int(float(summary["length"]) * 1000)
                if summary.get("time") is not None:
                    duration_s = int(summary["time"])

        return {
            "order_id": order_id,
            "stops": stops,
            "path": path,
            "source": source,
            "distance_meters": distance_m,
            "duration_seconds": duration_s,
        }
