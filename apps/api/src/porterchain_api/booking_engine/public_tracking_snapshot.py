"""Public live-tracking snapshot — map + ETA for website and customer track pages."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_api.models import Order
from porterchain_api.order_engine.buckets import IN_FLIGHT
from porterchain_services.maps.route_helpers import optimized_route_from_valhalla
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


def _format_eta_label(seconds: int) -> str:
    if seconds < 60:
        return "< 1 min"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours}h {rem}m"


def _osrm_eta(
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

    result = maps._osrm_route(origin_pt, destination)
    if not result or result.get("code") != "Ok" or not result.get("routes"):
        return None
    route = result["routes"][0]
    duration = int(route.get("duration", 0))
    distance = int(route.get("distance", 0))
    arrives_at = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat()
    return {
        "source": "osrm",
        "duration_seconds": duration,
        "distance_meters": distance,
        "polyline": route.get("geometry"),
        "arrives_at": arrives_at,
        "label": _format_eta_label(duration),
    }


def _valhalla_route(
    maps: MapsService,
    origin: tuple[float, float] | None,
    destination: tuple[float, float] | None,
) -> dict[str, Any] | None:
    if not origin or not destination:
        return None
    result = maps._valhalla_route(origin, destination)
    return optimized_route_from_valhalla(result)


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
    """Return public-safe live tracking: addresses, driver pin, route geometry, and ETA."""
    maps_service = maps or MapsService()
    translated = _translate_live(live_raw)
    pickup = order.pickup if isinstance(order.pickup, dict) else None
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else None
    pickup_coords = _coords_from_address(pickup)
    dropoff_coords = _coords_from_address(dropoff)
    driver_loc = translated.get("location")

    eta: dict[str, Any] | None = None
    if order.state not in DELIVERED_STATES:
        eta_origin = driver_loc or pickup_coords
        if eta_origin and dropoff_coords:
            eta = _osrm_eta(maps_service, eta_origin, dropoff_coords)
        if not eta and order.scheduled_at:
            eta = _scheduled_eta(order)

    optimized_route = (
        _valhalla_route(maps_service, pickup_coords, dropoff_coords)
        if pickup_coords and dropoff_coords
        else None
    )

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
