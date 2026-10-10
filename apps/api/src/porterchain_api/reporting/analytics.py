"""Ops analytics for a local delivery company — one call, compact numbers.

Margins come from ``reporting.margin`` (actual driver pay where recorded, the pay
plan otherwise). On-time = delivered within the grace window of the scheduled
time. Fill % = stops per route against ``target_stops_per_route``. Forecast is a
seasonal-naive weekday average per FSA over the last ``forecast_weeks`` weeks —
honest and explainable until volume justifies ML (see Settings → Future).
"""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.reporting.margin import margin_report

_POSTAL = re.compile(r"\b([ABCEGHJ-NPRSTVXY]\d[A-Z])\s?\d[A-Z]\d\b")
FAILED_STATES = {"FAILED", "FAILED_DELIVERY", "RETURN_TO_SENDER"}
ON_TIME_GRACE = timedelta(minutes=30)


def _fsa(addr: Any) -> str:
    if not isinstance(addr, dict):
        return "?"
    raw = str(addr.get("postal_code") or addr.get("postal") or addr.get("zip") or "").replace(" ", "").upper()
    if len(raw) >= 3 and raw[0].isalpha():
        return raw[:3]
    hit = _POSTAL.search(str(addr.get("formatted") or "").upper())
    return hit.group(1) if hit else "?"


def _pct(n: float, d: float) -> float | None:
    return round(n / d * 100, 1) if d else None


def _group(rows: list[dict[str, Any]], key: str, limit: int = 15) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, int]] = defaultdict(lambda: {"stops": 0, "revenue_cents": 0, "margin_cents": 0})
    for r in rows:
        a = agg[str(r.get(key) or "?")]
        a["stops"] += 1
        a["revenue_cents"] += r["revenue_cents"]
        a["margin_cents"] += r["margin_cents"]
    out = [
        {"key": k, **v, "margin_pct": _pct(v["margin_cents"], v["revenue_cents"])} for k, v in agg.items()
    ]
    out.sort(key=lambda r: -r["revenue_cents"])
    return out[:limit]


def _vehicle(o: Order) -> str:
    meta = o.compliance_metadata or {}
    stamped = (meta.get("analytics") or {}).get("vehicle")
    q = getattr(o, "quote", None)
    v = stamped or getattr(q, "vehicle_class", None) or meta.get("vehicle_class")
    return str(v or "?")


def analytics_stamp(o: Order) -> dict[str, str]:
    """FSA + vehicle captured at booking (see Order before_insert hook)."""
    out: dict[str, str] = {}
    fsa = _fsa(o.dropoff)
    if fsa != "?":
        out["fsa"] = fsa
    meta = o.compliance_metadata or {}
    q = getattr(o, "quote", None)
    v = getattr(q, "vehicle_class", None) or meta.get("vehicle_class") or meta.get("vehicle")
    if v:
        out["vehicle"] = str(v)
    return out


def _aware(dt: datetime | None) -> datetime | None:
    return dt.replace(tzinfo=UTC) if dt is not None and dt.tzinfo is None else dt


def forecast_by_fsa(
    history: list[tuple[datetime, str]], *, now: datetime, weeks: int = 6, days_ahead: int = 7, top: int = 8
) -> list[dict[str, Any]]:
    """Per FSA: expected orders for each of the next ``days_ahead`` days (weekday mean)."""
    since = now - timedelta(weeks=weeks)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for at, fsa in history:
        if at >= since:
            counts[fsa][at.date().isoformat()] += 1
    totals = sorted(counts, key=lambda f: -sum(counts[f].values()))[:top]
    out = []
    for fsa in totals:
        by_wd: dict[int, list[int]] = defaultdict(list)
        for w in range(weeks):
            for d in range(7):
                day = (since + timedelta(days=w * 7 + d)).date()
                by_wd[day.weekday()].append(counts[fsa].get(day.isoformat(), 0))
        days = []
        for i in range(1, days_ahead + 1):
            day = (now + timedelta(days=i)).date()
            vals = by_wd[day.weekday()] or [0]
            days.append({"day": day.isoformat(), "expected": round(sum(vals) / len(vals), 1)})
        out.append({"fsa": fsa, "days": days, "next7_total": round(sum(d["expected"] for d in days), 1)})
    return out


def ops_analytics(
    db: Session, *, days: int = 30, now: datetime | None = None, target_stops_per_route: int | None = None
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    if target_stops_per_route is None:
        from porterchain_api.admin_engine.platform_settings import finance_number

        target_stops_per_route = max(1, int(finance_number(db, "target_stops_per_route", 30.0)))
    since = now - timedelta(days=max(1, min(days, 366)))
    m = margin_report(db, days=days, now=now, stop_limit=100_000)
    stops = m["stops"]
    ids = [s["order_id"] for s in stops]
    meta = {
        o.id: o
        for o in (db.query(Order).filter(Order.id.in_(ids)).all() if ids else [])
    }
    for s in stops:
        o = meta.get(s["order_id"])
        s["fsa"] = (((o.compliance_metadata or {}).get("analytics") or {}).get("fsa") or _fsa(o.dropoff)) if o else "?"
        s["vehicle"] = _vehicle(o) if o else "?"

    # On-time: one query for delivered events.
    delivered = {}
    if ids:
        for ev in db.query(OrderEvent).filter(
            OrderEvent.order_id.in_(ids), OrderEvent.event_type == "order.delivered"
        ):
            delivered[ev.order_id] = _aware(ev.occurred_at)
    judged = on_time = 0
    for oid, o in meta.items():
        # Promise = SLA deadline when set, else scheduled time + grace.
        sched, done = _aware(o.sla_deadline_at or o.scheduled_at), delivered.get(oid)
        if sched and done:
            judged += 1
            on_time += int(done <= sched + (timedelta(0) if o.sla_deadline_at else ON_TIME_GRACE))

    window = (
        db.query(Order)
        .filter(Order.is_sandbox.is_(False), Order.scheduled_at >= since, Order.scheduled_at <= now)
        .all()
    )
    failed = [o for o in window if o.state in FAILED_STATES]
    routes = m["routes"]
    drivers: dict[str, dict[str, int]] = defaultdict(lambda: {"routes": 0, "stops": 0, "revenue_cents": 0})
    for r in routes:
        d = drivers[r["driver_id"]]
        d["routes"] += 1
        d["stops"] += r["stops"]
        d["revenue_cents"] += r["revenue_cents"]
    productivity = sorted(
        (
            {"driver_id": k, **v, "stops_per_route": round(v["stops"] / v["routes"], 1)}
            for k, v in drivers.items()
        ),
        key=lambda r: -r["stops"],
    )[:15]

    trend: dict[str, dict[str, int]] = defaultdict(lambda: {"stops": 0, "revenue_cents": 0, "margin_cents": 0})
    for s in stops:
        t = trend[s["day"]]
        t["stops"] += 1
        t["revenue_cents"] += s["revenue_cents"]
        t["margin_cents"] += s["margin_cents"]

    hist_since = now - timedelta(weeks=6)
    history = [
        (_aware(o.scheduled_at), _fsa(o.dropoff))
        for o in db.query(Order.scheduled_at, Order.dropoff).filter(
            Order.is_sandbox.is_(False), Order.scheduled_at >= hist_since, Order.scheduled_at <= now
        )
    ]
    from porterchain_api.admin_models import Driver
    from porterchain_api.merchant_models import Merchant

    merchant_rows = _group(stops, "merchant_id")
    mids = {r["key"] for r in merchant_rows}
    mnames = dict(db.query(Merchant.id, Merchant.company_name).filter(Merchant.id.in_(mids)).all()) if mids else {}
    for r in merchant_rows:
        r["name"] = mnames.get(r["key"]) or ("Retail / no merchant" if r["key"] == "?" else r["key"][:8])
    dids = [d["driver_id"] for d in productivity]
    dnames = dict(db.query(Driver.id, Driver.full_name).filter(Driver.id.in_(dids)).all()) if dids else {}
    for d in productivity:
        d["name"] = dnames.get(d["driver_id"]) or d["driver_id"][:8]
    t = m["totals"]
    return {
        "days": days,
        "generated_at": now.isoformat(),
        "kpis": {
            "orders": len(window),
            "delivered_stops": t["stops"],
            "revenue_cents": t["revenue_cents"],
            "margin_cents": t["margin_cents"],
            "margin_pct": t["margin_pct"],
            "cost_per_stop_cents": round(t["driver_cost_cents"] / t["stops"]) if t["stops"] else None,
            "on_time_pct": _pct(on_time, judged),
            "on_time_sample": judged,
            "failed": len(failed),
            "failed_pct": _pct(len(failed), len(window)),
            "routes": t["routes"],
            "fill_pct": _pct(sum(r["stops"] for r in routes), len(routes) * target_stops_per_route),
            "estimated_cost_share": t["estimated_share"],
            "target_stops_per_route": target_stops_per_route,
        },
        "margin_by": {
            "merchant": merchant_rows,
            "fsa": _group(stops, "fsa"),
            "vehicle": _group(stops, "vehicle"),
            "route": [
                {k: r[k] for k in ("route_id", "stops", "revenue_cents", "margin_cents", "margin_pct", "cost_source")}
                for r in routes[:15]
            ],
        },
        "drivers": productivity,
        "trend": [{"day": k, **v} for k, v in sorted(trend.items())],
        "forecast": forecast_by_fsa([h for h in history if h[0]], now=now),
        "failed_recent": [
            {"order_id": o.id, "order_number": o.order_number, "state": o.state, "fsa": _fsa(o.dropoff)}
            for o in failed[-10:]
        ],
    }
