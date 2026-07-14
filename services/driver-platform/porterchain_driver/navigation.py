"""Navigation session — Fleetbase GPS, OSRM ETA, Valhalla routes (masterrule §3).

Google Maps renders on the client only. This service orchestrates:
- Fleetbase live tracking via booking_engine.TrackingService + adapter
- OSRM ETA polylines via porterchain_services.MapsService
- Valhalla optimized routes via MapsService
- Driver location pings for replay / fallback position
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from porterchain_api.booking_engine.tracking_service import TrackingService
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_services.maps.route_helpers import optimized_route_from_valhalla
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
                "gps": "fleetbase",
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
        *,
        fleetbase_bridge: Any = None,
    ) -> dict:
        return self.session(db, driver, order_id, settings, fleetbase_bridge=fleetbase_bridge)

    def route_for_stops(
        self,
        db: Session,
        driver: Any,
        route_id: str,
        settings: Settings,
        *,
        fleetbase_bridge: Any = None,
    ) -> dict:
        session = self.route_session(db, driver, route_id, settings, fleetbase_bridge=fleetbase_bridge)
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
        *,
        fleetbase_bridge: Any = None,
    ) -> dict[str, Any]:
        from porterchain_api.models import Order

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
        fleetbase_location = translated.get("location")

        pickup_route = None
        delivery_route = None
        if current_location and pickup:
            pickup_route = self._osrm_route(current_location, pickup, label="pickup")
        if pickup and dropoff:
            delivery_route = self._valhalla_route(pickup, dropoff)
        elif current_location and dropoff:
            delivery_route = self._osrm_route(current_location, dropoff, label="delivery")

        eta_origin = fleetbase_location or current_location or pickup
        eta = self._osrm_route(eta_origin, dropoff, label="eta") if eta_origin and dropoff else None

        optimized_route = delivery_route
        route_polyline = None
        if fleetbase_bridge and order.fleetbase_order_id:
            route_data = fleetbase_bridge.fetch_route(order.fleetbase_order_id)
            if route_data:
                route_polyline = route_data.get("polyline") or route_data.get("route_polyline")

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
            "driver_location": fleetbase_location or current_location,
            "gps_source": "fleetbase" if fleetbase_location else ("porterchain_ping" if current_location else None),
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
                "gps": "fleetbase",
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
        *,
        fleetbase_bridge: Any = None,
    ) -> dict[str, Any]:
        from porterchain_driver.stops import StopsService

        stops = StopsService().stops_for_route(db, driver.id, route_id)
        orders_seen: set[str] = set()
        sessions: list[dict[str, Any]] = []
        for stop in stops:
            if stop.order_id in orders_seen:
                continue
            orders_seen.add(stop.order_id)
            try:
                sessions.append(
                    self.session(db, driver, stop.order_id, settings, fleetbase_bridge=fleetbase_bridge)
                )
            except LookupError:
                continue

        primary = sessions[0] if sessions else None
        return {
            "route_id": route_id,
            "sessions": sessions,
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
            "geofences": [g for s in sessions for g in s.get("geofences", [])],
            "last_updated": datetime.now(UTC).isoformat(),
        }

    def _fetch_live(self, db: Session, settings: Settings, order: Any) -> dict[str, Any] | None:
        if not order.fleetbase_order_id:
            return None
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
        live_raw: dict[str, Any] | None,
    ) -> dict[str, float] | None:
        loc = translated.get("location")
        if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
            return {"lat": float(loc["lat"]), "lng": float(loc["lng"])}

        from porterchain_api.driver_models import DriverLocationPing

        ping = (
            db.query(DriverLocationPing)
            .filter(DriverLocationPing.driver_id == driver.id)
            .order_by(DriverLocationPing.created_at.desc())
            .first()
        )
        if ping:
            return {"lat": ping.lat, "lng": ping.lng}
        return None

    def _osrm_route(
        self,
        origin: dict[str, float] | tuple[float, float],
        destination: tuple[float, float],
        *,
        label: str = "osrm",
    ) -> dict[str, Any] | None:
        if isinstance(origin, dict):
            origin_pt = (float(origin["lat"]), float(origin["lng"]))
        else:
            origin_pt = origin
        result = self._maps._osrm_route(origin_pt, destination)
        if not result or result.get("code") != "Ok" or not result.get("routes"):
            return None
        route = result["routes"][0]
        duration = int(route.get("duration", 0))
        distance = int(route.get("distance", 0))
        return {
            "source": "osrm",
            "label": label,
            "duration_seconds": duration,
            "distance_meters": distance,
            "polyline": route.get("geometry"),
            "arrives_at": (datetime.now(UTC) + timedelta(seconds=duration)).isoformat(),
            "eta_label": _format_eta_label(duration),
        }

    def _valhalla_route(
        self,
        origin: tuple[float, float] | None,
        destination: tuple[float, float] | None,
    ) -> dict[str, Any] | None:
        if not origin or not destination:
            return None
        result = self._maps._valhalla_route(origin, destination)
        route = optimized_route_from_valhalla(result)
        if not route:
            return None
        duration = route["duration_seconds"]
        return {
            **route,
            "label": "optimized",
            "eta_label": _format_eta_label(duration),
        }

    def _tracking_history(self, db: Session, order_id: str) -> list[dict[str, Any]]:
        from porterchain_api.models import OrderEvent

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
        from porterchain_api.driver_models import DriverLocationPing

        rows = (
            db.query(DriverLocationPing)
            .filter(DriverLocationPing.driver_id == driver_id)
            .order_by(DriverLocationPing.created_at.asc())
            .limit(limit)
            .all()
        )
        return [
            {
                "lat": r.lat,
                "lng": r.lng,
                "at": r.created_at.isoformat() if r.created_at else None,
                "source": "driver_ping",
            }
            for r in rows
        ]

    def _build_replay(
        self,
        history: list[dict[str, Any]],
        activity: list[dict[str, Any]],
        live_raw: dict[str, Any] | None,
        ping_frames: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
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
                add_frame(float(loc["lat"]), float(loc["lng"]), item.get("at"), "fleetbase_activity")

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
                        "fleetbase_live",
                    )

        frames.sort(key=lambda f: str(f.get("at") or ""))
        return frames

    def _stop_geofences(self, order: Any) -> list[dict[str, Any]]:
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
                        "radius_m": 150,
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
            "AT_DESTINATION",
        )
        return {
            "order_state": order_state,
            "fleetbase_status": translated.get("fleetbase_status"),
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
