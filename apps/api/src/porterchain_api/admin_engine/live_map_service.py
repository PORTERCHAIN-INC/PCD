"""Live map snapshot — adapter-fed driver positions + PC-mirror order stops.

Policy: the browser gets Google tiles only; Fleetbase positions arrive via the
adapter (read-only polled REST — never SocketCluster in web apps). Order stop
markers come from the Porterchain mirror. Route geometry is computed by
MapsService (Valhalla); without it we fall back to straight legs between stops,
labeled source="direct".
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import (
    _coords,
    _driver_location,
)
from porterchain_api.admin_models import Driver
from porterchain_api.models import Order
from porterchain_services.maps.polyline import decode_polyline

logger = logging.getLogger(__name__)

ACTIVE_LIMIT = 200
# ~1.1 km cells at GTA latitudes — coarse density without Google HeatmapLayer.
DENSITY_CELL = 0.01


def _density_cells(orders: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[int, int], dict[str, Any]] = {}
    for o in orders:
        for s in o.get("stops") or []:
            try:
                lat = float(s["lat"])
                lng = float(s["lng"])
            except (KeyError, TypeError, ValueError):
                continue
            key = (int(lat / DENSITY_CELL), int(lng / DENSITY_CELL))
            cell = buckets.get(key)
            if cell is None:
                buckets[key] = {
                    "lat": (key[0] + 0.5) * DENSITY_CELL,
                    "lng": (key[1] + 0.5) * DENSITY_CELL,
                    "weight": 1,
                }
            else:
                cell["weight"] += 1
    return sorted(buckets.values(), key=lambda c: -c["weight"])


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
        self._adapter = adapter
        self._maps = maps

    def _get_adapter(self) -> Any:
        if self._adapter is None:
            try:
                from porterchain_api.config import get_settings
                from porterchain_api.services.fleetbase_integration import (
                    get_fleetbase_integration,
                )

                adapter = get_fleetbase_integration(get_settings())
                self._adapter = adapter if adapter.is_enabled else None
            except Exception as exc:
                logger.info("Fleetbase adapter unavailable for live map: %s", exc)
                self._adapter = None
        return self._adapter

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
            .filter(Order.state.in_(IN_FLIGHT))
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

        drivers_out: list[dict[str, Any]] = []
        drivers_source = "unavailable"
        adapter = self._get_adapter()
        if adapter is not None:
            try:
                fleetbase_drivers = adapter.list_drivers()
            except Exception as exc:  # the map must render even if positions fail
                logger.warning("Fleetbase driver positions unavailable: %s", exc)
                fleetbase_drivers = []
            pc_drivers = (
                db.query(Driver).filter(Driver.fleetbase_driver_id.isnot(None)).all()
            )
            by_fleetbase = {d.fleetbase_driver_id: d for d in pc_drivers}
            for fd in fleetbase_drivers:
                fid = fd.get("id") or fd.get("uuid")
                loc = _driver_location(fd)
                if not fid or not loc:
                    continue
                match = by_fleetbase.get(fid)
                online = fd.get("online")
                if not isinstance(online, bool):
                    online = str(fd.get("status") or "").lower() in {"online", "active"}
                drivers_out.append(
                    {
                        "id": match.id if match else str(fid),
                        "fleetbase_driver_id": str(fid),
                        "name": match.full_name if match else str(fd.get("name") or "Driver"),
                        "lat": loc[0],
                        "lng": loc[1],
                        "online": online,
                    }
                )
            drivers_source = "fleetbase" if fleetbase_drivers else "unavailable"

        density = _density_cells(out_orders)
        zones: list[dict[str, Any]] = []
        zones_source = "unavailable"
        if adapter is not None:
            try:
                zones = adapter.list_zone_overlays()
                zones_source = "fleetbase" if zones else "unavailable"
            except Exception as exc:
                logger.warning("Fleetbase zone overlays unavailable: %s", exc)

        return {
            "drivers": drivers_out,
            "orders": out_orders,
            "drivers_source": drivers_source,
            "density": density,
            "zones": zones,
            "zones_source": zones_source,
        }

    def playback(self, db: Session, order_id: str) -> dict[str, Any]:
        """Fleetbase position breadcrumbs for client-side route playback."""
        order = db.get(Order, order_id)
        if not order:
            raise LookupError(f"Order {order_id} not found")

        adapter = self._get_adapter()
        if adapter is None or not order.fleetbase_order_id:
            return {
                "order_id": order_id,
                "fleetbase_order_id": order.fleetbase_order_id,
                "points": [],
                "source": "none",
                "message": "Order not synced to Fleetbase or bridge offline",
            }

        subject_uuid: str | None = None
        if order.assigned_driver_id:
            driver = db.get(Driver, order.assigned_driver_id)
            if driver and driver.fleetbase_driver_id:
                subject_uuid = driver.fleetbase_driver_id

        try:
            hist = adapter.position_history(
                order_uuid=order.fleetbase_order_id,
                subject_uuid=subject_uuid,
            )
        except Exception as exc:
            logger.warning("Position history failed for %s: %s", order_id, exc)
            hist = {"points": [], "source": "none"}

        return {
            "order_id": order_id,
            "fleetbase_order_id": order.fleetbase_order_id,
            "points": hist.get("points") or [],
            "source": hist.get("source") or "none",
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
