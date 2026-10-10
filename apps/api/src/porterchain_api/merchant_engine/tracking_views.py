"""Merchant tracking views — snapshot sanitize, history, geofences, ETA cache."""

from __future__ import annotations

import time
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, PricingZone
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.config import Settings
from porterchain_api.domain.catalog_labels import order_state_label
from porterchain_api.merchant_engine.rbac import MerchantContext

_ETA_CACHE_TTL_SECONDS = 90
_eta_cache: dict[str, tuple[float, dict[str, Any]]] = {}

_TRACKING_ERRORS = {
    "order_not_found": "That order was not found.",
    "tracking_not_found": "No shipment matches that tracking number, order number, or PO.",
}

_REPLAY_SOURCE_ALIASES = {
    "last_known": "live",
    "osrm": "eta",
    "valhalla": "route",
}


def tracking_error_message(code: str) -> str:
    return _TRACKING_ERRORS.get(code, _TRACKING_ERRORS["order_not_found"])


class AmbiguousTrackingQuery(LookupError):
    """One PO, several deliveries — the caller must pick one (BK)."""

    def __init__(self, query: str, orders: list[Order]) -> None:
        super().__init__("tracking_ambiguous")
        self.query = query
        self.orders = orders

    @property
    def message(self) -> str:
        return (
            f"{len(self.orders)} shipments share PO {self.query}. Pick the one you want to track."
        )

    def choices(self) -> list[dict[str, Any]]:
        return [
            {
                "order_id": o.id,
                "order_number": o.order_number,
                "tracking_number": o.tracking_number,
                "state": o.state,
                "dropoff": (o.dropoff or {}).get("formatted") if isinstance(o.dropoff, dict) else None,
                "scheduled_at": o.scheduled_at.isoformat() if o.scheduled_at else None,
            }
            for o in self.orders
        ]


def public_track_url(
    settings: Settings,
    tracking_number: str | None,
    *,
    is_sandbox: bool = False,
) -> str | None:
    if not tracking_number or is_sandbox:
        return None
    return f"{settings.website_url.rstrip('/')}/track/{tracking_number}"


def coords_from_address(addr: dict[str, Any] | None) -> tuple[float, float] | None:
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


def merchant_replay_frame(frame: Any) -> Any:
    if not isinstance(frame, dict):
        return frame
    source = str(frame.get("source") or "")
    alias = _REPLAY_SOURCE_ALIASES.get(source, source)
    return {**frame, "source": alias}


def merchant_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    payload["display_state"] = order_state_label(str(payload.get("state") or ""))
    payload.pop("live", None)
    eta = payload.get("eta")
    if isinstance(eta, dict):
        payload["eta"] = {k: v for k, v in eta.items() if k != "source"}
    route = payload.get("optimized_route")
    if isinstance(route, dict):
        cleaned = {k: v for k, v in route.items() if k != "source"}
        cleaned.setdefault("polyline_encoding", "google")
        payload["optimized_route"] = cleaned
    status = payload.get("delivery_status")
    if isinstance(status, dict):
        status["label"] = order_state_label(str(status.get("order_state") or payload.get("state") or ""))
    replay = payload.get("replay")
    if isinstance(replay, list):
        payload["replay"] = [merchant_replay_frame(frame) for frame in replay]
    return payload


def delivery_status(order_state: str, *, in_flight: tuple[str, ...]) -> dict[str, Any]:
    return {
        "order_state": order_state,
        "label": order_state_label(order_state),
        "in_transit": order_state in in_flight,
        "delivered": order_state in ("DELIVERED", "POD_COMPLETED", "INVOICED", "CLOSED"),
    }


def format_eta_label(seconds: int) -> str:
    if seconds < 60:
        return "< 1 min"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes} min"
    hours, rem = divmod(minutes, 60)
    return f"{hours}h {rem}m"


def get_cached_eta(cache_key: str) -> dict[str, Any] | None:
    entry = _eta_cache.get(cache_key)
    if not entry:
        return None
    expires_at, eta = entry
    if time.time() > expires_at:
        _eta_cache.pop(cache_key, None)
        return None
    return eta


def set_cached_eta(cache_key: str, eta: dict[str, Any]) -> None:
    _eta_cache[cache_key] = (time.time() + _ETA_CACHE_TTL_SECONDS, eta)


def driver_info(db: Session, order: Order, live_raw: dict[str, Any] | None) -> dict[str, Any] | None:
    fb_driver = None
    if live_raw:
        tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
        fb_driver = live_raw.get("driver") or tracker.get("driver") if isinstance(tracker, dict) else None

    driver = None
    if order.assigned_driver_id:
        driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()

    if driver:
        return {
            "id": driver.id,
            "name": driver.full_name,
            "phone": driver.phone,
            "is_online": fb_driver.get("online") if isinstance(fb_driver, dict) else None,
            "rating": driver.rating,
        }
    if isinstance(fb_driver, dict):
        return {
            "id": fb_driver.get("id"),
            "name": fb_driver.get("name"),
            "phone": fb_driver.get("phone"),
        }
    return None


def vehicle_info(db: Session, order: Order, live_raw: dict[str, Any] | None) -> dict[str, Any] | None:
    fb_vehicle = None
    if live_raw and isinstance(live_raw.get("tracker"), dict):
        tracker = live_raw["tracker"]
        fb_vehicle = tracker.get("vehicle") or tracker.get("order", {}).get("vehicle")

    vehicle = None
    if order.assigned_driver_id:
        driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
        if driver and driver.vehicles:
            vehicle = next((v for v in driver.vehicles if v.is_active), driver.vehicles[0])

    if vehicle:
        return {
            "id": vehicle.id,
            "label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})",
            "vehicle_class": vehicle.vehicle_class,
            "plate_number": vehicle.plate_number,
        }
    if isinstance(fb_vehicle, dict):
        return {
            "id": fb_vehicle.get("id"),
            "label": fb_vehicle.get("name") or fb_vehicle.get("plate_number"),
            "vehicle_class": fb_vehicle.get("vehicle_class"),
            "plate_number": fb_vehicle.get("plate_number"),
        }
    return None


def tracking_history(db: Session, order_id: str) -> list[dict[str, Any]]:
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
            "payload": ev.payload,
            "location": (ev.payload or {}).get("location") if isinstance(ev.payload, dict) else None,
        }
        for ev in events
    ]


def build_replay(
    history: list[dict[str, Any]],
    activity: list[dict[str, Any]],
    live_raw: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_frame(lat: float, lng: float, at: str | None, source: str) -> None:
        key = f"{lat:.5f},{lng:.5f},{at}"
        if key in seen:
            return
        seen.add(key)
        frames.append({"lat": lat, "lng": lng, "at": at, "source": source})

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
                    "live",
                )

    frames.sort(key=lambda f: str(f.get("at") or ""))
    return frames


def merchant_geofences(
    db: Session,
    ctx: MerchantContext,
    *,
    order: Order | None = None,
) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    codes = list(ctx.merchant.delivery_zones or [])
    if codes:
        rows = (
            db.query(PricingZone)
            .filter(PricingZone.is_active.is_(True), PricingZone.code.in_(codes))
            .all()
        )
        for z in rows:
            zones.append(
                {
                    "id": z.id,
                    "code": z.code,
                    "name": z.name,
                    "geofence_type": "delivery_zone",
                    "bounds": z.bounds or {},
                }
            )
        for code in codes:
            if not any(z["code"] == code for z in zones):
                zones.append(
                    {
                        "id": code,
                        "code": code,
                        "name": code,
                        "geofence_type": "delivery_zone",
                        "bounds": {},
                    }
                )

    if order:
        for label, addr in (("pickup", order.pickup), ("dropoff", order.dropoff)):
            coords = coords_from_address(addr if isinstance(addr, dict) else None)
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
