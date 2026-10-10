"""Navigation session — Redis GPS, OSRM ETA, Valhalla routes (masterrule §3).

Google Maps renders on the client only. This service orchestrates:
- PorterChain tracking via booking_engine.TrackingService
- OSRM ETA polylines via porterchain_services.MapsService
- Valhalla optimized routes via MapsService
- Redis last-known for nav origin
- Shift trace replay (road-snapped when opened)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.config import Settings
from porterchain_api.dispatch_engine.nav_geometry_cache import read_nav_geometry, write_nav_geometry
from porterchain_api.booking_engine.tracking_translator import TrackingTranslator
from porterchain_services.maps.service import MapsService

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def _coords_from_address(addr: dict[str, Any] | None) -> tuple[float, float] | None:
    if not addr or not isinstance(addr, dict):
        return None
    lat, lng = addr.get("lat"), addr.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


STOP_GEOFENCE_RADIUS_M = 150

# Paused 2026-10-04. Drivers may arrive and then confirm pickup or delivery
# without a GPS fix inside the stop circle. Web, iOS, and Android all call
# arrive_stop, so this one switch covers those apps. Set True to restore.
ENFORCE_STOP_PRESENCE = False


def assert_driver_inside_stop(driver_id: str, order: Any, stop_id: str) -> None:
    """Fail closed when last-known GPS is outside the stop circle.

    Missing GPS does not block arrive — last-known is a cache, not a hard lock.
    While ENFORCE_STOP_PRESENCE is False, a fix outside the circle does not block either.
    """
    if not ENFORCE_STOP_PRESENCE:
        return
    from porterchain_api.driver_engine.last_known import distance_m, read_last_known

    known = read_last_known(driver_id)
    if known is None:
        return
    label = "pickup" if str(stop_id).endswith("-pickup") else "dropoff"
    fence = next(
        (g for g in NavigationService._stop_geofences(order) if g.get("geofence_type") == label),
        None)
    if not fence:
        return
    center = fence.get("center") if isinstance(fence.get("center"), dict) else {}
    try:
        clat, clng = float(center["lat"]), float(center["lng"])
    except (KeyError, TypeError, ValueError):
        return
    radius = int(fence.get("radius_m") or STOP_GEOFENCE_RADIUS_M)
    if int(distance_m(known.lat, known.lng, clat, clng)) > radius:
        raise ValueError("not_at_stop")


def _format_eta_label(seconds: int) -> str:
    if seconds < 60:
        return "< 1 min"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours}h {rem}m"


class NavigationService:
    def __init__(self) -> None:
        self._tracking = TrackingService()
        self._maps = MapsService()

    def idle_session(self, driver: Any) -> dict[str, Any]:
        """Empty navigation session when driver has no active job."""
        return {
            "idle": True,
            "order_id": None,
            "tracking_number": None,
            "order_number": None,
            "state": "idle",
            "message": "no_active_job",
            "pickup": None,
            "dropoff": None,
            "pickup_route": None,
            "delivery_route": None,
            "optimized_route": None,
            "eta": None,
            "route_polyline": None,
            "navigation_url": None,
            "current_location": None,
            "driver_location": None,
            "gps_source": None,
            "delivery_status": {"label": "No active job", "code": "idle"},
            "stops": [],
            "timeline": [],
            "replay": [],
            "geofences": [],
            "traffic": {"layer_available": True, "source": "google_maps_ui"},
            "offline_maps": {
                "enabled": False,
                "future_ready": True,
                "message": "Offline map tile cache — planned; session geometry available for prefetch",
            },
            "routing_engines": {
                "gps": "last_known",
                "eta": "osrm",
                "optimized_route": "valhalla",
                "map_display": "google_maps",
            },
            "driver": {"id": driver.id, "availability": getattr(driver, "availability", "offline")},
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def route_for_order(
        self,
        db: Session,
        driver: Any,
        order_id: str,
        settings: Settings,
    ) -> dict:
        return self.session(db, driver, order_id, settings)

    def route_for_stops(
        self,
        db: Session,
        driver: Any,
        route_id: str,
        settings: Settings,
    ) -> dict:
        session = self.route_session(db, driver, route_id, settings)
        return {
            "route_id": route_id,
            "stops": session["stops"],
            "route_polyline": session.get("route_polyline"),
        }

    def session(
        self,
        db: Session,
        driver: Any,
        order_id: str,
        settings: Settings,
    ) -> dict[str, Any]:
        from porterchain_api.booking_models import Order

        order = (
            db.query(Order)
            .filter(Order.id == order_id, Order.assigned_driver_id == driver.id)
            .first()
        )
        if not order:
            raise LookupError("order_not_found")

        live_raw = self._fetch_live(db, settings, order)
        translated = self._translate_live(live_raw)
        pickup = _coords_from_address(order.pickup if isinstance(order.pickup, dict) else None)
        dropoff = _coords_from_address(order.dropoff if isinstance(order.dropoff, dict) else None)

        current_location = self._resolve_current_location(db, driver, translated, live_raw)
        live_location = translated.get("location")

        pickup_route = None
        delivery_route = None
        if current_location and pickup:
            origin_pt = (float(current_location["lat"]), float(current_location["lng"]))
            cached_pickup = read_nav_geometry(order.id, origin_pt, pickup)
            pickup_route = cached_pickup or self._eta_leg(current_location, pickup, label="pickup")
            if pickup_route and not cached_pickup:
                write_nav_geometry(order.id, origin_pt, pickup, pickup_route)
        if pickup and dropoff:
            cached_delivery = read_nav_geometry(order.id, pickup, dropoff)
            delivery_route = cached_delivery or self._route_leg(pickup, dropoff)
            if delivery_route and not cached_delivery:
                write_nav_geometry(order.id, pickup, dropoff, delivery_route)
        elif current_location and dropoff:
            delivery_route = self._eta_leg(current_location, dropoff, label="delivery")

        eta_origin = live_location or current_location or pickup
        eta = self._eta_leg(eta_origin, dropoff, label="eta") if eta_origin and dropoff else None

        optimized_route = delivery_route
        route_polyline = None
        for bag in (delivery_route, pickup_route, eta):
            if isinstance(bag, dict) and bag.get("polyline"):
                route_polyline = bag.get("polyline")
                break

        history = self._tracking_history(db, order.id)
        ping_replay = self._driver_ping_replay(db, driver.id)
        replay = self._build_replay(history, translated.get("activity") or [], live_raw, ping_replay)

        from porterchain_driver.stops import StopsService

        stops_svc = StopsService()
        pickup_stop = stops_svc._order_to_stop(order, "pickup")  # noqa: SLF001
        dropoff_stop = stops_svc._order_to_stop(order, "dropoff")  # noqa: SLF001

        return {
            "order_id": order.id,
            "tracking_number": order.tracking_number,
            "order_number": order.order_number,
            "state": order.state,
            "pickup": order.pickup,
            "dropoff": order.dropoff,
            "pickup_route": pickup_route,
            "delivery_route": delivery_route,
            "optimized_route": optimized_route,
            "eta": eta,
            "route_polyline": route_polyline,
            "navigation_url": _maps_url(order.pickup, order.dropoff),
            "current_location": current_location,
            "driver_location": live_location or current_location,
            "gps_source": "last_known" if live_location else ("porterchain_ping" if current_location else None),
            "live": translated,
            "delivery_status": self._delivery_status(order.state, translated),
            "stops": [
                {
                    "stop_id": pickup_stop.stop_id,
                    "stop_type": "pickup",
                    "address": pickup_stop.address,
                    "sequence": pickup_stop.sequence,
                    "status": pickup_stop.status,
                },
                {
                    "stop_id": dropoff_stop.stop_id,
                    "stop_type": "dropoff",
                    "address": dropoff_stop.address,
                    "sequence": dropoff_stop.sequence,
                    "status": dropoff_stop.status,
                },
            ],
            "timeline": history,
            "replay": replay,
            "geofences": self._stop_geofences(order),
            "traffic": {"layer_available": True, "source": "google_maps_ui"},
            "offline_maps": {
                "enabled": False,
                "future_ready": True,
                "message": "Offline map tile cache — planned; session geometry available for prefetch",
            },
            "routing_engines": {
                "gps": "last_known",
                "eta": "osrm",
                "optimized_route": "valhalla",
                "map_display": "google_maps",
            },
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def route_session(
        self,
        db: Session,
        driver: Any,
        route_id: str,
        settings: Settings,
    ) -> dict[str, Any]:
        from porterchain_driver.stops import StopsService

        stops = StopsService().stops_for_route(db, driver.id, route_id)
        primary = None
        first_oid = next((s.order_id for s in stops if s.order_id), None)
        if first_oid:
            try:
                primary = self.session(
                    db, driver, first_oid, settings
                )
            except LookupError:
                primary = None

        return {
            "route_id": route_id,
            "sessions": [primary] if primary else [],
            "stops": [
                {
                    "stop_id": s.stop_id,
                    "stop_type": s.stop_type,
                    "address": s.address,
                    "sequence": s.sequence,
                    "order_id": s.order_id,
                    "status": s.status,
                }
                for s in stops
            ],
            "route_polyline": primary.get("optimized_route", {}).get("polyline") if primary else None,
            "current_location": primary.get("current_location") if primary else None,
            "eta": primary.get("eta") if primary else None,
            "geofences": list(primary.get("geofences") or []) if primary else [],
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _fetch_live(self, db: Session, settings: Settings, order: Any) -> dict[str, Any] | None:
        try:
            return self._tracking.get_live_tracking(db, settings, order)
        except Exception:
            return None

    def _translate_live(self, live_raw: dict[str, Any] | None) -> dict[str, Any]:
        if not live_raw:
            return TrackingTranslator.translate(None)
        tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
        coords = live_raw.get("coordinates")
        merged = {**tracker, **(coords if isinstance(coords, dict) else {})}
        if live_raw.get("eta"):
            merged["eta"] = live_raw["eta"]
        if live_raw.get("driver"):
            merged["driver"] = live_raw["driver"]
        if live_raw.get("status"):
            merged["status"] = live_raw["status"]
        return TrackingTranslator.translate(merged)

    def _resolve_current_location(
        self,
        db: Session,
        driver: Any,
        translated: dict[str, Any],
        live_raw: dict[str, Any] | None) -> dict[str, float] | None:
        loc = translated.get("location")
        if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
            return {"lat": float(loc["lat"]), "lng": float(loc["lng"])}

        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(str(driver.id))
        if known is not None:
            return {"lat": known.lat, "lng": known.lng}
        return None

    def _eta_leg(
        self,
        origin: dict[str, float] | tuple[float, float],
        destination: tuple[float, float],
        *,
        label: str = "osrm") -> dict[str, Any] | None:
        if isinstance(origin, dict):
            origin_pt = (float(origin["lat"]), float(origin["lng"]))
        else:
            origin_pt = origin
        result = self._maps.eta_between(origin_pt, destination)
        if not result:
            return None
        duration = int(result.get("duration_seconds", 0))
        return {
            **result,
            "source": result.get("source") or "osrm",
            "label": label,
            "arrives_at": (datetime.now(UTC) + timedelta(seconds=duration)).isoformat(),
            "eta_label": _format_eta_label(duration),
        }

    def _route_leg(
        self,
        origin: tuple[float, float] | None,
        destination: tuple[float, float] | None) -> dict[str, Any] | None:
        if not origin or not destination:
            return None
        route = self._maps.optimized_route(origin, destination)
        if not route:
            return None
        duration = route["duration_seconds"]
        return {
            **route,
            "label": "optimized",
            "eta_label": _format_eta_label(duration),
        }

    def _tracking_history(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        from porterchain_api.booking_models import OrderEvent

        events = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order_id)
            .order_by(OrderEvent.occurred_at.asc())
            .all()
        )
        return [
            {
                "event_type": ev.event_type,
                "label": ev.event_type.replace(".", " ").replace("_", " ").title(),
                "from_state": ev.from_state,
                "to_state": ev.to_state,
                "occurred_at": ev.occurred_at.isoformat() if ev.occurred_at else None,
                "location": (ev.payload or {}).get("location") if isinstance(ev.payload, dict) else None,
            }
            for ev in events
        ]

    def _driver_ping_replay(self, db: Session, driver_id: str, *, limit: int = 120) -> list[dict[str, Any]]:
        del db, limit
        from porterchain_api.driver_engine.last_known import read_last_known

        known = read_last_known(driver_id)
        if known is None:
            return []
        return [
            {
                "lat": known.lat,
                "lng": known.lng,
                "at": known.recorded_at.isoformat() if known.recorded_at else None,
                "source": "last_known",
            }
        ]

    def _build_replay(
        self,
        history: list[dict[str, Any]],
        activity: list[dict[str, Any]],
        live_raw: dict[str, Any] | None,
        ping_frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
        frames: list[dict[str, Any]] = []
        seen: set[str] = set()

        def add_frame(lat: float, lng: float, at: str | None, source: str) -> None:
            key = f"{lat:.5f},{lng:.5f},{at}"
            if key in seen:
                return
            seen.add(key)
            frames.append({"lat": lat, "lng": lng, "at": at, "source": source})

        for item in ping_frames:
            add_frame(float(item["lat"]), float(item["lng"]), item.get("at"), item.get("source", "driver_ping"))

        for item in activity:
            loc = item.get("location")
            if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                add_frame(float(loc["lat"]), float(loc["lng"]), item.get("at"), "activity")

        for ev in history:
            loc = ev.get("location")
            if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                add_frame(float(loc["lat"]), float(loc["lng"]), ev.get("occurred_at"), "order_event")

        if live_raw:
            tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
            for key in ("coordinates", "position", "location"):
                loc = live_raw.get(key) or (tracker.get(key) if isinstance(tracker, dict) else None)
                if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
                    add_frame(
                        float(loc["lat"]),
                        float(loc["lng"]),
                        live_raw.get("last_updated") or live_raw.get("updated_at"),
                        "last_known",
                    )

        frames.sort(key=lambda f: str(f.get("at") or ""))
        return frames

    @staticmethod
    def _stop_geofences(order: Any) -> list[dict[str, Any]]:
        zones: list[dict[str, Any]] = []
        for label, addr in (("pickup", order.pickup), ("dropoff", order.dropoff)):
            coords = _coords_from_address(addr if isinstance(addr, dict) else None)
            if coords:
                zones.append(
                    {
                        "id": f"{order.id}-{label}",
                        "name": f"{label.title()} — {order.tracking_number}",
                        "geofence_type": label,
                        "center": {"lat": coords[0], "lng": coords[1]},
                        "radius_m": STOP_GEOFENCE_RADIUS_M,
                    }
                )
        return zones

    def _delivery_status(self, order_state: str, translated: dict[str, Any]) -> dict[str, Any]:
        in_flight = order_state in (
            "DRIVER_ASSIGNED",
            "DRIVER_ACCEPTED",
            "DRIVER_EN_ROUTE",
            "AT_PICKUP",
            "PICKED_UP",
            "IN_TRANSIT",
            "AT_DESTINATION")
        return {
            "order_state": order_state,
            "label": order_state.replace("_", " ").title(),
            "in_transit": in_flight,
            "delivered": order_state in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"),
        }


def _maps_url(pickup: dict, dropoff: dict) -> str | None:
    plat, plng = pickup.get("lat"), pickup.get("lng")
    dlat, dlng = dropoff.get("lat"), dropoff.get("lng")
    if None in (plat, plng, dlat, dlng):
        return None
    return (
        f"https://www.google.com/maps/dir/?api=1&origin={plat},{plng}"
        f"&destination={dlat},{dlng}&travelmode=driving"
    )
