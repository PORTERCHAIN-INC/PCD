"""Assignment scoring — capability/skills/window filters + Valhalla matrix.

Used by the worker `score_suggestions` job only. Request GET never calls this.
Live online/position comes from Driver duty + Redis last_known.

Suggestions are recommendation-only — a person still assigns the van.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.dispatch_suggestions_service import (
    CANDIDATE_CAP,
    _coords,
    _driver_online,
    score_candidate,
)
from porterchain_api.admin_models import Driver
from porterchain_api.booking_engine.compliance_metadata import requires_medical_certified
from porterchain_api.booking_models import Order
from porterchain_api.domain.customer_goods import canonical_vehicle_id, persist_vehicle_class, vehicle_classes_match

logger = logging.getLogger(__name__)

CACHE_KEY = "porterchain:dispatch:suggestions:{order_id}"
CACHE_TTL_SECONDS = 45
MATRIX_CANDIDATE_CAP = 20  # drivers with live position included in Valhalla matrix
WINDOW_MISS_PENALTY = 40.0


def _parse_dt(raw: Any) -> datetime | None:
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def order_pickup_window(order: Order) -> tuple[datetime | None, datetime | None]:
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    rich = meta.get("stops")
    if isinstance(rich, list):
        pickups = [
            s
            for s in rich
            if isinstance(s, dict) and str(s.get("type") or "").lower() == "pickup"
        ]
        if pickups:
            p = sorted(pickups, key=lambda s: s.get("sequence", 0))[0]
            return _parse_dt(p.get("time_window_start")), _parse_dt(p.get("time_window_end"))
    window = meta.get("delivery_window") if isinstance(meta.get("delivery_window"), dict) else {}
    return _parse_dt(window.get("start")), _parse_dt(window.get("end"))


def required_skills(meta: dict[str, Any]) -> list[str]:
    raw = meta.get("required_skills") or meta.get("skills")
    if isinstance(raw, list):
        return [str(s).strip().lower() for s in raw if str(s).strip()]
    if meta.get("cold_chain") and isinstance(meta["cold_chain"], dict) and meta["cold_chain"].get("required"):
        return ["cold_chain"]
    return []


def driver_skills(driver: Driver) -> set[str]:
    docs = driver.documents if isinstance(driver.documents, dict) else {}
    raw = docs.get("skills") or docs.get("certifications") or []
    skills: set[str] = set()
    if isinstance(raw, list):
        skills |= {str(s).strip().lower() for s in raw if str(s).strip()}
    if driver.medical_transport_certified:
        skills.add("medical")
        skills.add("medical_transport")
    return skills


_BACKGROUND_PASSED = frozenset({"passed", "cleared", "approved"})


def driver_verification_gap(driver: Driver) -> str | None:
    """D-27: incomplete Admin verification → not assignable / not scorable."""
    from porterchain_api.driver_engine.verification_sources import doc_entry

    if not getattr(driver, "license_verified", False):
        return "driver_license_not_verified"
    if not getattr(driver, "insurance_verified", False):
        return "driver_insurance_not_verified"
    bg = str(getattr(driver, "background_check_status", "") or "").lower()
    if bg not in _BACKGROUND_PASSED:
        return "driver_background_check_incomplete"
    # Expired docs (status=expired) should already clear flags; belt-and-suspenders.
    for key, code in (
        ("insurance", "driver_insurance_expired"),
        ("license", "driver_license_expired"),
        ("vehicle_registration", "driver_vehicle_registration_expired"),
    ):
        entry = doc_entry(driver, key)
        if str(entry.get("status") or "").lower() == "expired":
            return code
    # Abstract rejection is an onboarding gate when enabled — not a hard CT exclude
    # unless ops already recorded a rejected abstract attempt.
    return None


def hard_filter_driver(
    driver: Driver,
    *,
    medical_required: bool,
    required_class: str | None,
    classes: set[str],
    skills_needed: list[str],
) -> str | None:
    """Return exclusion reason, or None if the driver may be scored."""
    gap = driver_verification_gap(driver)
    if gap:
        return {
            "driver_license_not_verified": "License not verified",
            "driver_insurance_not_verified": "Insurance not verified",
            "driver_background_check_incomplete": "Background check incomplete",
            "driver_insurance_expired": "Insurance expired",
            "driver_license_expired": "License expired",
            "driver_vehicle_registration_expired": "Vehicle registration expired",
        }.get(gap, gap)
    if medical_required and not driver.medical_transport_certified:
        return "Not medical-transport certified"
    # D-28: required class with no registered vehicles → hard exclude (not soft-rank).
    if required_class and not classes:
        return f"No vehicles registered (need {required_class})"
    if required_class and classes and not vehicle_classes_match(required_class, classes):
        return f"No {canonical_vehicle_id(required_class)} vehicle"
    if skills_needed:
        have = driver_skills(driver)
        missing = [s for s in skills_needed if s not in have]
        if missing:
            return f"Missing skills: {', '.join(missing)}"
    return None


def window_penalty(
    *,
    eta_minutes: float | None,
    window_end: datetime | None,
    now: datetime | None = None,
) -> tuple[float, str | None]:
    if eta_minutes is None or window_end is None:
        return 0.0, None
    ref = now or datetime.now(UTC).replace(tzinfo=None)
    arrival = ref.timestamp() + eta_minutes * 60
    if arrival > window_end.timestamp():
        return WINDOW_MISS_PENALTY, "ETA misses pickup window"
    return 0.0, None


def cache_key(order_id: str) -> str:
    return CACHE_KEY.format(order_id=order_id)


def read_suggestions_cache(order_id: str) -> dict[str, Any] | None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        raw = get_redis_client().get(cache_key(order_id))
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except Exception as exc:  # noqa: BLE001
        logger.debug("suggestions cache read failed: %s", exc)
        return None


def write_suggestions_cache(order_id: str, payload: dict[str, Any]) -> None:
    try:
        from porterchain_shared.redis_client import get_redis_client

        body = {**payload, "computed_at": datetime.now(UTC).isoformat(), "source": "cacheable"}
        get_redis_client().setex(cache_key(order_id), CACHE_TTL_SECONDS, json.dumps(body))
    except Exception as exc:  # noqa: BLE001
        logger.debug("suggestions cache write failed: %s", exc)


def enqueue_score_job(order_id: str) -> None:
    try:
        from porterchain_api.dispatch_engine.routing_jobs import enqueue_routing_job

        enqueue_routing_job({"action": "score_suggestions", "order_id": order_id})
    except Exception as exc:  # noqa: BLE001
        logger.info("score_suggestions enqueue failed: %s", exc)


def compute_ranked_suggestions(
    db: Session,
    order_id: str,
    *,
    adapter: Any = None,
    maps: Any = None,
) -> dict[str, Any]:
    """Full scored ranking with hard filters + Valhalla matrix when possible."""
    from porterchain_api.order_engine.buckets import IN_FLIGHT

    order = db.get(Order, order_id)
    if not order:
        raise LookupError(f"Order {order_id} not found")

    pickup_coords = _coords(order.pickup or {})
    meta = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
    required_class = meta.get("vehicle_class") or getattr(
        getattr(order, "quote", None), "vehicle_class", None
    )
    medical_required = requires_medical_certified(meta)
    skills_needed = required_skills(meta)
    _win_start, win_end = order_pickup_window(order)
    now = datetime.now(UTC).replace(tzinfo=None)

    drivers = (
        db.query(Driver)
        .filter(Driver.status == "APPROVED")
        .order_by(Driver.rating.desc().nullslast())
        .limit(100)
        .all()
    )
    loads = dict(
        db.query(Order.assigned_driver_id, func.count(Order.id))
        .filter(Order.state.in_(IN_FLIGHT), Order.assigned_driver_id.isnot(None))
        .group_by(Order.assigned_driver_id)
        .all()
    )
    classes_by_driver: dict[str, set[str]] = {
        d.id: {v.vehicle_class for v in d.vehicles if v.is_active and v.vehicle_class}
        for d in drivers
    }

    filtered_out: list[dict[str, str]] = []
    eligible: list[Driver] = []
    for d in drivers:
        reason = hard_filter_driver(
            d,
            medical_required=medical_required,
            required_class=required_class,
            classes=classes_by_driver.get(d.id, set()),
            skills_needed=skills_needed,
        )
        if reason:
            filtered_out.append({"id": d.id, "name": d.full_name, "reason": reason})
        else:
            eligible.append(d)

    from porterchain_api.driver_engine.last_known import read_last_known
    from porterchain_api.spatial.h3_index import cell as h3_cell
    from porterchain_api.spatial.h3_index import pick_nearby

    del adapter  # leftover GET inverted — last_known + duty only

    def base_key(d: Driver) -> tuple[int, int, float]:
        online = bool(d.is_online) or d.availability == "online"
        return (0 if online else 1, loads.get(d.id, 0), -(d.rating or 0.0))

    positions: dict[str, tuple[float, float, str | None]] = {}
    locations: dict[str, tuple[float, float]] = {}
    for d in eligible:
        known = read_last_known(d.id)
        if known:
            positions[d.id] = (known.lat, known.lng, known.h3 or h3_cell(known.lat, known.lng))
        if d.id in positions:
            lat, lng, _h3 = positions[d.id]
            locations[d.id] = (lat, lng)

    nearby_ids = pick_nearby(pickup_coords, positions) if pickup_coords else []
    by_id = {d.id: d for d in eligible}
    if nearby_ids:
        live_pool = [by_id[i] for i in nearby_ids if i in by_id]
        live_pool = sorted(live_pool, key=base_key)[:MATRIX_CANDIDATE_CAP]
    else:
        live_pool = sorted(eligible, key=base_key)[:MATRIX_CANDIDATE_CAP]
    live_ids = {d.id for d in live_pool[:CANDIDATE_CAP]}

    if maps is None and pickup_coords:
        from porterchain_services.maps.service import MapsService

        maps = MapsService()

    matrix_source: str | None = None
    eta_by_driver: dict[str, tuple[float | None, float | None, str]] = {}
    positioned = [d for d in live_pool if d.id in locations]
    if positioned and pickup_coords and maps:
        sources = [locations[d.id] for d in positioned]
        matrix, matrix_source = maps.matrix_durations(
            sources,
            [pickup_coords],
            vehicle_class=str(required_class) if required_class else None,
        )
        if matrix and len(matrix) == len(positioned):
            for i, d in enumerate(positioned):
                cell = matrix[i][0] if matrix[i] else (None, None)
                seconds, meters = cell
                eta_by_driver[d.id] = (
                    round(seconds / 60, 1) if seconds is not None else None,
                    round(meters / 1000, 1) if meters is not None else None,
                    matrix_source or "matrix",
                )
        else:
            # Per-leg fallback for the smaller live_ids set.
            for d in live_pool:
                if d.id not in live_ids or d.id not in locations:
                    continue
                meters, seconds, src = maps.route_distance_meters(
                    [locations[d.id], pickup_coords],
                    vehicle_class=str(required_class) if required_class else None,
                )
                eta_by_driver[d.id] = (
                    round(seconds / 60, 1) if seconds is not None else None,
                    round(meters / 1000, 1) if meters is not None else None,
                    src or "routing",
                )
            matrix_source = "route_fallback"

    suggestions: list[dict[str, Any]] = []
    for d in eligible:
        load = loads.get(d.id, 0)
        classes = classes_by_driver.get(d.id, set())
        capability = (
            None if not required_class or not classes else vehicle_classes_match(required_class, classes)
        )
        online = _driver_online(None, d)
        eta_min, deadhead_km, source = eta_by_driver.get(d.id, (None, None, "no_position"))
        win_pen, win_reason = window_penalty(eta_minutes=eta_min, window_end=win_end, now=now)

        reasons: list[str] = []
        if eta_min is not None:
            reasons.append(f"{eta_min:.0f} min to pickup")
        else:
            reasons.append("No live position")
        reasons.append("No active load" if load == 0 else f"{load} active delivery(ies)")
        if d.rating:
            reasons.append(f"{d.rating:.1f}★")
        if not online:
            reasons.append("Offline")
        if capability is True:
            reasons.append(f"{required_class} ready")
        if win_reason:
            reasons.append(win_reason)

        base = score_candidate(
            eta_minutes=eta_min,
            active_orders=load,
            rating=d.rating,
            online=online,
            capability_match=capability,
        )
        suggestions.append(
            {
                "id": d.id,
                "name": d.full_name,
                "rating": d.rating,
                "online": online,
                "active_orders": load,
                "eta_minutes": eta_min,
                "deadhead_km": deadhead_km,
                "eta_source": source,
                "capability_match": capability,
                "score": round(base + win_pen, 1),
                "reasons": reasons,
            }
        )

    suggestions.sort(key=lambda s: s["score"])
    return {
        "order_id": order_id,
        "pickup_coords": bool(pickup_coords),
        "vehicle_class": persist_vehicle_class(required_class) if required_class else required_class,
        "medical_required": medical_required,
        "required_skills": skills_needed,
        "matrix_source": matrix_source,
        "filtered_out": filtered_out,
        "filtered_out_count": len(filtered_out),
        "drivers": suggestions,
    }
