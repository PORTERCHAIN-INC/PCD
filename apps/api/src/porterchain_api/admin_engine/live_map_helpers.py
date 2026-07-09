"""Shared helpers and constants for the live operations map."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from porterchain_api.models import Order

# GTA default viewport when no markers present.
DEFAULT_CENTER = {"lat": 43.6532, "lng": -79.3832}

VEHICLE_STATUS_MAP = {
    "available": "available",
    "idle": "available",
    "online": "assigned",
    "busy": "busy",
    "on_trip": "busy",
    "break": "busy",
    "offline": "offline",
    "maintenance": "maintenance",
}


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _parse_iso_naive(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is not None:
        return parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("longitude")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lng = math.radians(lng2 - lng1)
    a = (
        math.sin(d_lat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lng / 2) ** 2
    )
    return 2 * r * math.asin(math.sqrt(a))


def _driver_ref(driver_id: str) -> str:
    return f"PCD-{driver_id[:6].upper()}"


def _vehicle_ref(vehicle_id: str) -> str:
    return f"PCV-{vehicle_id[:6].upper()}"


def _merchant_ref(merchant_id: str) -> str:
    return f"PCM-{merchant_id[:6].upper()}"


def _order_vehicle_class(order: Order) -> str | None:
    quote = order.quote
    return quote.vehicle_class if quote else None
