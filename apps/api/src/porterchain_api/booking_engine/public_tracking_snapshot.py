"""Public live-tracking snapshot — map + ETA for website and customer track pages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.booking_engine.public_address import public_address_snapshot
from porterchain_api.dispatch_engine.nav_geometry_cache import read_nav_geometry, write_nav_geometry
from porterchain_api.booking_engine.tracking_normalize import TrackingFacade
from porterchain_api.booking_models import Order
from porterchain_api.order_engine.buckets import IN_FLIGHT
from porterchain_services.maps.service import MapsService

DELIVERED_STATES = frozenset({"DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"})


def _coords_from_address(addr: dict[str, Any] | None) -> tuple[float, float] | None:
    if not addr or not isinstance(addr, dict):
        return None
    lat = addr.get("lat")
    lng = addr.get("lng")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _translate_live(live_raw: dict[str, Any] | None) -> dict[str, Any]:
    return TrackingFacade.translate_live(live_raw)


def _format_eta_label(seconds: int) -> str:
    if seconds < 60:
        return "< 1 min"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours}h {rem}m"


def _road_eta(
    maps: MapsService,
    origin: dict[str, float] | tuple[float, float] | None,
    destination: tuple[float, float] | None,
) -> dict[str, Any] | None:
    if not origin or not destination:
        return None
    if isinstance(origin, dict):
        o_lat, o_lng = origin.get("lat"), origin.get("lng")
        if o_lat is None or o_lng is None:
            return None
        origin_pt = (float(o_lat), float(o_lng))
    else:
        origin_pt = origin

    eta = maps.eta_between(origin_pt, destination)
    if not eta:
        return None
    duration = int(eta.get("duration_seconds", 0))
    arrives_at = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat()
    return {
        **eta,
        "arrives_at": arrives_at,
        "label": _format_eta_label(duration),
    }


def _scheduled_eta(order: Order) -> dict[str, Any]:
    scheduled = order.scheduled_at
    if scheduled is None:
        raise ValueError("scheduled_at required")
    if scheduled.tzinfo is None:
        scheduled = scheduled.replace(tzinfo=UTC)
    return {
        "source": "scheduled",
        "arrives_at": scheduled.isoformat(),
        "label": scheduled.strftime("%I:%M %p").lstrip("0"),
    }


def build_public_live_tracking(
    order: Order,
    live_raw: dict[str, Any] | None,
    *,
    maps: MapsService | None = None,
) -> dict[str, Any]:
    """Return public-safe live tracking: city-level addresses, driver pin, route geometry, and ETA."""
    maps_service = maps or MapsService()
    translated = _translate_live(live_raw)
    pickup_raw = order.pickup if isinstance(order.pickup, dict) else None
    dropoff_raw = order.dropoff if isinstance(order.dropoff, dict) else None
    pickup = public_address_snapshot(pickup_raw)
    dropoff = public_address_snapshot(dropoff_raw)
    pickup_coords = _coords_from_address(pickup_raw)
    dropoff_coords = _coords_from_address(dropoff_raw)
    driver_loc = translated.get("location")
    if not driver_loc and getattr(order, "assigned_driver_id", None):
        from porterchain_api.dispatch_engine.driver_pin import driver_pin

        driver_loc = driver_pin(order.assigned_driver_id)

    eta: dict[str, Any] | None = None
    if order.state not in DELIVERED_STATES:
        eta_origin = driver_loc or pickup_coords
        if eta_origin and dropoff_coords:
            eta = _road_eta(maps_service, eta_origin, dropoff_coords)
        if not eta and order.scheduled_at:
            eta = _scheduled_eta(order)

    optimized_route = None
    if pickup_coords and dropoff_coords:
        cached = read_nav_geometry(order.id, pickup_coords, dropoff_coords)
        if cached:
            optimized_route = cached
        else:
            optimized_route = maps_service.optimized_route(pickup_coords, dropoff_coords)
            if optimized_route:
                write_nav_geometry(order.id, pickup_coords, dropoff_coords, optimized_route)

    return {
        "pickup": pickup,
        "dropoff": dropoff,
        "driver_location": driver_loc,
        "eta": eta,
        "optimized_route": optimized_route,
        "last_updated": translated.get("last_updated"),
        "delivery_status": {
            "order_state": order.state,
            "label": order.state.replace("_", " ").title(),
            "in_transit": order.state in IN_FLIGHT,
            "delivered": order.state in DELIVERED_STATES,
        },
    }
