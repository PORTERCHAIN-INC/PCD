"""Ranked driver suggestions for the dispatch queue (decision support only).

Data ownership:
- Compliance, rating, active load, vehicle capability → Porterchain DB mirror.
- Live position / online state → Redis ops mirror (worker-refreshed).
- Distance/ETA → MapsService on the worker (`score_suggestions`), never on GET.

GET is cache-first. Cache miss returns ``source=pending`` and enqueues compute.
Assignment itself still flows through /v1/admin/dispatch/orders/{id}/assign.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CANDIDATE_CAP = 6  # max live Fleetbase position lookups (legacy sync path / matrix seed)
NO_POSITION_ETA_MIN = 180.0
LOAD_PENALTY_MIN = 8.0
OFFLINE_PENALTY_MIN = 12.0
CAPABILITY_PENALTY_MIN = 6.0
RATING_BONUS_PER_STAR = 1.5


def _coords(addr: dict | None) -> tuple[float, float] | None:
    if not addr:
        return None
    lat = addr.get("lat") or addr.get("latitude")
    lng = addr.get("lng") or addr.get("lon") or addr.get("longitude")
    try:
        if lat is None or lng is None:
            return None
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def _driver_location(payload: dict[str, Any] | None) -> tuple[float, float] | None:
    """Best-effort parse of a Fleetbase driver resource into (lat, lng)."""
    if not payload:
        return None
    body = payload.get("driver") if isinstance(payload.get("driver"), dict) else payload
    loc = body.get("location")
    if isinstance(loc, dict):
        c = _coords(loc)
        if c:
            return c
        coords = loc.get("coordinates")
        if isinstance(coords, (list, tuple)) and len(coords) == 2:
            try:
                return float(coords[1]), float(coords[0])  # GeoJSON [lng, lat]
            except (TypeError, ValueError):
                pass
    return _coords(body)


def _driver_online(payload: dict[str, Any] | None, driver: Any) -> bool:
    if payload:
        body = payload.get("driver") if isinstance(payload.get("driver"), dict) else payload
        online = body.get("online")
        if isinstance(online, bool):
            return online
        status = str(body.get("status") or "").lower()
        if status:
            return status in {"online", "active"}
    return bool(getattr(driver, "is_online", False)) or getattr(driver, "availability", None) == "online"


def score_candidate(
    *,
    eta_minutes: float | None,
    active_orders: int,
    rating: float | None,
    online: bool,
    capability_match: bool | None,
) -> float:
    """Lower is better. Pure function — unit-tested without DB or network."""
    # Prefer real ETA; missing GPS ranks far behind (D-28) instead of fake 25 min.
    eta = eta_minutes if eta_minutes is not None else NO_POSITION_ETA_MIN
    score = eta + LOAD_PENALTY_MIN * active_orders
    score -= RATING_BONUS_PER_STAR * (rating if rating is not None else 3.0)
    if not online:
        score += OFFLINE_PENALTY_MIN
    if capability_match is False:
        score += CAPABILITY_PENALTY_MIN
    return round(score, 1)


class DispatchSuggestionsService:
    def __init__(self, adapter: Any = None, maps: Any = None) -> None:
        self._adapter = adapter
        self._maps = maps

    def suggest(self, db: Session, order_id: str, *, refresh: bool = False) -> dict[str, Any]:
        from porterchain_api.admin_engine.control_tower.scoring import (
            enqueue_score_job,
            read_suggestions_cache,
        )
        from porterchain_api.booking_models import Order

        order = db.get(Order, order_id)
        if not order:
            raise LookupError(f"Order {order_id} not found")

        cached = None if refresh else read_suggestions_cache(order_id)
        if cached and isinstance(cached.get("drivers"), list):
            return {**cached, "source": "cache"}

        enqueue_score_job(order_id)
        stale = read_suggestions_cache(order_id) if refresh else None
        if stale and isinstance(stale.get("drivers"), list):
            return {**stale, "source": "stale"}
        return {
            "order_id": order_id,
            "drivers": [],
            "filtered_out": [],
            "filtered_out_count": 0,
            "source": "pending",
        }
