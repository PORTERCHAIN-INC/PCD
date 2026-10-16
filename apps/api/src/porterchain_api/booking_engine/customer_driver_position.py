"""Customer-facing driver position for the in-app live tracking map.

Rules (all enforced here, unit tested in tests/test_customer_driver_position.py):
- Only the customer who owns the order may ask (else "not found", no leak).
- Only while the shipment is active: driver heading to pickup, at pickup, or
  out for delivery. Never before a driver is moving, never after delivery,
  cancellation or failure.
- Only if the driver's GPS sharing is allowed by the GPS policy (admin switch,
  per-driver opt-out, and the driver's recorded consent).
- Position is coarse: rounded to 3 decimals (about 100 m) and dropped when
  older than 10 minutes.
- No driver contact data is returned (no phone, email, id, rating).
- Rate limited per customer and order.
"""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime
from typing import Any, Callable

ACTIVE_STATES = frozenset(
    {"DRIVER_EN_ROUTE", "AT_PICKUP", "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION"}
)
COARSE_DECIMALS = 3
MAX_AGE_SECONDS = 600
MIN_INTERVAL_SECONDS = 5.0

_lock = threading.Lock()
_last_call: dict[str, float] = {}


class RateLimited(Exception):
    def __init__(self, retry_after: float) -> None:
        super().__init__("rate_limited")
        self.retry_after = max(1, int(retry_after + 0.999))


def check_rate(
    key: str, *, now: float | None = None, interval: float = MIN_INTERVAL_SECONDS
) -> None:
    t = time.monotonic() if now is None else now
    with _lock:
        last = _last_call.get(key)
        if last is not None and t - last < interval:
            raise RateLimited(interval - (t - last))
        _last_call[key] = t
        if len(_last_call) > 50_000:  # bounded memory
            _last_call.clear()


def reset_rate_limits() -> None:
    with _lock:
        _last_call.clear()


def _parse(ts: Any) -> datetime | None:
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=UTC)
    if isinstance(ts, str) and ts:
        try:
            d = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
        return d if d.tzinfo else d.replace(tzinfo=UTC)
    return None


def load_order_and_driver(db: Any, tracking_number: str) -> tuple[Any, Any]:
    """Order by tracking number and its assigned driver (either may be None)."""
    from porterchain_api.admin_models import Driver
    from porterchain_api.booking_models import Order

    order = db.query(Order).filter(Order.tracking_number == tracking_number).first()
    driver_id = getattr(order, "assigned_driver_id", None) if order else None
    driver = db.get(Driver, driver_id) if driver_id else None
    return order, driver


def coarse_position(
    state: Any,
    pin: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Shared privacy filter for any driver position shown outside ops.

    Active shipment only, fresh (<= MAX_AGE_SECONDS) only, rounded to COARSE_DECIMALS
    (~100 m). Anything else -> None. Never returns source, heading, speed or driver ids.
    """
    if str(state or "").upper() not in ACTIVE_STATES:
        return None
    if not pin or pin.get("lat") is None or pin.get("lng") is None:
        return None
    recorded = _parse(pin.get("recorded_at"))
    current = now or datetime.now(UTC)
    if recorded is None or (current - recorded).total_seconds() > MAX_AGE_SECONDS:
        return None
    try:
        lat, lng = float(pin["lat"]), float(pin["lng"])
    except (TypeError, ValueError):
        return None
    return {
        "lat": round(lat, COARSE_DECIMALS),
        "lng": round(lng, COARSE_DECIMALS),
        "recorded_at": recorded.replace(microsecond=0).isoformat(),
    }


def unavailable(reason: str) -> dict[str, Any]:
    return {"available": False, "reason": reason, "position": None}


def customer_driver_position(
    order: Any,
    *,
    customer_id: str,
    driver: Any | None,
    pin: dict[str, Any] | None,
    gps_allowed: Callable[[Any], bool],
    now: datetime | None = None,
) -> dict[str, Any] | None:
    """Return the payload, or None when the order isn't this customer's (caller -> 404)."""
    if (
        order is None
        or not customer_id
        or getattr(order, "customer_id", None) != customer_id
    ):
        return None
    state = str(getattr(order, "state", "") or "").upper()
    if state not in ACTIVE_STATES:
        return unavailable("not_active")
    if not getattr(order, "assigned_driver_id", None) or driver is None:
        return unavailable("no_driver")
    if not gps_allowed(driver):
        return unavailable("sharing_off")
    if not pin or pin.get("lat") is None or pin.get("lng") is None:
        return unavailable("no_signal")
    position = coarse_position(state, pin, now=now)
    if position is None:
        return unavailable("stale")
    return {"available": True, "reason": None, "position": position}
