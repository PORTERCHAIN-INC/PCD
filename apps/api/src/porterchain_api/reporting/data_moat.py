"""§8.2 — proprietary operational datasets (dwell time, SLA, margin, ETA)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver, MerchantContract
from porterchain_api.booking_engine.compliance_metadata import delivery_window_end
from porterchain_api.config import Settings
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_services.maps.service import MapsService

ON_TIME_GRACE_MINUTES = 30

DWELL_EVENT_PAIRS: tuple[tuple[str, str, str], ...] = (
    ("pickup_dwell", "order.arrived_pickup", "order.pickup_completed"),
    ("dropoff_dwell", "order.arrived_dropoff", "order.delivered"),
)

PICKUP_FALLBACK_END = "order.picked_up"


def _event_durations_minutes(
    db: Session,
    *,
    merchant_id: str | None = None,
    since: datetime | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    q = db.query(OrderEvent).join(Order, Order.id == OrderEvent.order_id)
    if merchant_id:
        q = q.filter(Order.merchant_id == merchant_id)
    if since:
        q = q.filter(OrderEvent.occurred_at >= since)
    events = q.order_by(OrderEvent.occurred_at.asc()).limit(limit * 8).all()
    by_order: dict[str, dict[str, datetime]] = {}
    order_merchant: dict[str, str | None] = {}
    for ev in events:
        order_merchant[ev.order_id] = None
        bucket = by_order.setdefault(ev.order_id, {})
        if ev.event_type not in bucket:
            ts = ev.occurred_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=UTC)
            bucket[ev.event_type] = ts

    if order_merchant:
        for oid, mid in db.query(Order.id, Order.merchant_id).filter(Order.id.in_(order_merchant)).all():
            order_merchant[oid] = mid

    rows: list[dict[str, Any]] = []
    for order_id, times in by_order.items():
        for label, start_type, end_type in DWELL_EVENT_PAIRS:
            end = times.get(end_type)
            start = times.get(start_type)
            if label == "pickup_dwell" and (not start or not end):
                start = start or times.get("order.arrived_pickup")
                end = end or times.get(PICKUP_FALLBACK_END)
            if not start or not end:
                continue
            minutes = max(0.0, (end - start).total_seconds() / 60.0)
            rows.append(
                {
                    "order_id": order_id,
                    "merchant_id": order_merchant.get(order_id),
                    "dwell_type": label,
                    "minutes": round(minutes, 1),
                    "started_at": start.isoformat(),
                    "ended_at": end.isoformat(),
                }
            )
            if len(rows) >= limit:
                return rows
    return rows


def dwell_time_dataset(
    db: Session,
    *,
    merchant_id: str | None = None,
    window_days: int = 90,
    limit: int = 500,
) -> dict[str, Any]:
    since = datetime.now(UTC) - timedelta(days=window_days)
    rows = _event_durations_minutes(db, merchant_id=merchant_id, since=since, limit=limit)
    by_type: dict[str, list[float]] = {}
    for row in rows:
        by_type.setdefault(row["dwell_type"], []).append(row["minutes"])
    summary = {
        dwell_type: {
            "samples": len(values),
            "avg_minutes": round(sum(values) / len(values), 1) if values else 0.0,
            "p90_minutes": round(sorted(values)[max(0, int(len(values) * 0.9) - 1)], 1) if values else 0.0,
        }
        for dwell_type, values in by_type.items()
    }
    return {
        "window_days": window_days,
        "merchant_id": merchant_id,
        "samples": len(rows),
        "summary": summary,
        "records": rows[:100],
    }


def network_sla_benchmark(db: Session, *, window_days: int = 30) -> dict[str, Any]:
    from porterchain_api.admin_engine.business_metrics import assess_on_time_delivery
    from porterchain_api.order_engine.buckets import DONE_STATES

    baseline = assess_on_time_delivery(db, window_days=window_days)
    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    delivered = (
        db.query(Order)
        .filter(Order.created_at >= cutoff, Order.state.in_(DONE_STATES))
        .limit(2000)
        .all()
    )
    window_on_time = 0
    window_total = 0
    grace = timedelta(minutes=ON_TIME_GRACE_MINUTES)
    for order in delivered:
        window_end = delivery_window_end(order.compliance_metadata)
        if not window_end:
            continue
        window_total += 1
        event = (
            db.query(OrderEvent)
            .filter(OrderEvent.order_id == order.id, OrderEvent.event_type == "order.delivered")
            .order_by(OrderEvent.occurred_at.desc())
            .first()
        )
        delivered_at = event.occurred_at if event else order.updated_at
        if delivered_at and delivered_at.tzinfo is None:
            delivered_at = delivered_at.replace(tzinfo=UTC)
        if delivered_at <= window_end + grace:
            window_on_time += 1
    food_medical_pct = (
        round(window_on_time / window_total * 100, 2) if window_total else baseline["pct"]
    )
    return {
        "window_days": window_days,
        "network_on_time_pct": baseline["pct"],
        "vertical_window_sla_pct": food_medical_pct,
        "vertical_window_samples": window_total,
        "slo_target_pct": baseline["slo_target_pct"],
        "meets_slo": baseline["meets_slo"],
        "grace_minutes": ON_TIME_GRACE_MINUTES,
    }


def margin_intelligence(
    db: Session,
    *,
    merchant_id: str | None = None,
    window_days: int = 30,
) -> dict[str, Any]:
    from porterchain_api.order_engine.buckets import DONE_STATES

    cutoff = datetime.now(UTC) - timedelta(days=window_days)
    q = db.query(Order).filter(
        Order.created_at >= cutoff,
        Order.state.in_(DONE_STATES),
    )
    if merchant_id:
        q = q.filter(Order.merchant_id == merchant_id)
    orders = q.limit(5000).all()
    revenue_cents = sum(o.amount_cents for o in orders)
    contract_share: dict[str, float] = {}
    for contract in db.query(MerchantContract).filter(MerchantContract.is_active.is_(True)).all():
        rules = contract.rules if isinstance(contract.rules, dict) else {}
        share = rules.get("driver_share_pct") or rules.get("margin_pct")
        if share is not None:
            contract_share[contract.merchant_id] = float(share)

    estimated_cost_cents = 0
    for order in orders:
        if not order.merchant_id:
            estimated_cost_cents += int(order.amount_cents * 0.68)
            continue
        share = contract_share.get(order.merchant_id, 68.0)
        estimated_cost_cents += int(order.amount_cents * (share / 100.0))

    gross_margin_cents = revenue_cents - estimated_cost_cents
    margin_pct = round(gross_margin_cents / revenue_cents * 100, 2) if revenue_cents else 0.0
    active_contracts = (
        db.query(func.count(MerchantContract.id))
        .filter(MerchantContract.is_active.is_(True))
        .scalar()
        or 0
    )
    return {
        "window_days": window_days,
        "merchant_id": merchant_id,
        "orders": len(orders),
        "revenue_cents": revenue_cents,
        "estimated_cost_cents": estimated_cost_cents,
        "gross_margin_cents": gross_margin_cents,
        "gross_margin_pct": margin_pct,
        "active_custom_contracts": int(active_contracts),
        "model": "contract_share_or_68pct_default",
    }


def _driver_ping_location(driver: Driver | None, live_raw: dict[str, Any] | None) -> tuple[float, float] | None:
    if driver:
        perf = driver.performance if isinstance(driver.performance, dict) else {}
        loc = perf.get("last_location") or perf.get("location")
        if isinstance(loc, dict) and loc.get("lat") is not None and loc.get("lng") is not None:
            return float(loc["lat"]), float(loc["lng"])
    if live_raw:
        location = live_raw.get("location") or live_raw.get("current_location") or {}
        if isinstance(location, dict) and location.get("lat") is not None:
            return float(location["lat"]), float(location["lng"])
    return None


def own_ping_eta(db: Session, settings: Settings, order_id: str) -> dict[str, Any] | None:
    """ETA from Porterchain driver ping + OSRM (§8.2.4)."""
    from porterchain_api.booking_engine.tracking_service import TrackingService

    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        return None
    dropoff = order.dropoff if isinstance(order.dropoff, dict) else {}
    if dropoff.get("lat") is None or dropoff.get("lng") is None:
        return {"order_id": order.id, "model": "own_ping_osrm", "eta": None, "reason": "dropoff_coordinates_missing"}

    driver = None
    if order.assigned_driver_id:
        driver = db.query(Driver).filter(Driver.id == order.assigned_driver_id).first()
    live_raw = TrackingService().get_live_tracking(db, settings, order)
    origin = _driver_ping_location(driver, live_raw)
    if not origin:
        return {"order_id": order.id, "model": "own_ping_osrm", "eta": None, "reason": "driver_ping_unavailable"}

    destination = (float(dropoff["lat"]), float(dropoff["lng"]))
    maps = MapsService()
    eta = maps.eta_between(origin, destination)
    if not eta:
        return {"order_id": order.id, "model": "own_ping_osrm", "eta": None, "reason": "routing_unavailable"}

    duration = int(eta.get("duration_seconds", 0))
    arrives_at = (datetime.now(UTC) + timedelta(seconds=duration)).isoformat()
    return {
        "order_id": order.id,
        "model": "own_ping_osrm",
        "driver_location": {"lat": origin[0], "lng": origin[1]},
        "eta": {
            "source": "own_ping",
            "duration_seconds": duration,
            "distance_meters": int(eta.get("distance_meters", 0)),
            "arrives_at": arrives_at,
        },
    }
