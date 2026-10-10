"""Merchant reporting engine — SQL aggregates scoped to merchant (masterrule §11)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver, Vehicle
from porterchain_api.booking_engine.compliance_metadata import delivery_window_end
from porterchain_api.booking_models import Invoice, Order, OrderEvent
from porterchain_api.domain.states import OrderState
from porterchain_api.order_engine.buckets import DONE_STATES, FAILED_STATES

RETURNED_STATES = ("RETURN_TO_SENDER",)
ON_TIME_GRACE_MINUTES = 30

REPORT_TYPES = (
    "executive",
    "delivery",
    "orders",
    "invoices",
    "drivers",
    "vehicles",
    "destinations",
    "claims",
    "history",
)


def _now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def month_start(reference: datetime | None = None) -> datetime:
    ref = (reference or _now()).replace(tzinfo=None)
    return datetime(ref.year, ref.month, 1)


def merchant_avg_duration_hours(
    db: Session,
    merchant_id: str,
    from_type: str,
    to_type: str,
    *,
    since: datetime | None = None,
) -> float | None:
    order_ids = [r[0] for r in db.query(Order.id).filter(Order.merchant_id == merchant_id).all()]
    if not order_ids:
        return 0.0
    query = db.query(OrderEvent).filter(
        OrderEvent.order_id.in_(order_ids),
        OrderEvent.event_type.in_((from_type, to_type)),
    )
    if since:
        query = query.filter(OrderEvent.occurred_at >= since)
    events = query.order_by(OrderEvent.occurred_at.asc()).all()
    by_order: dict[str, dict[str, datetime]] = {}
    for ev in events:
        bucket = by_order.setdefault(ev.order_id, {})
        if ev.event_type not in bucket:
            ts = ev.occurred_at.replace(tzinfo=None) if ev.occurred_at.tzinfo else ev.occurred_at
            bucket[ev.event_type] = ts
    deltas: list[float] = []
    for times in by_order.values():
        if from_type in times and to_type in times:
            delta = (times[to_type] - times[from_type]).total_seconds() / 3600
            if delta >= 0:
                deltas.append(delta)
    return round(sum(deltas) / len(deltas), 1) if deltas else None


def monthly_trends(db: Session, merchant_id: str, months: int = 6) -> dict[str, Any]:
    labels: list[str] = []
    orders_series: list[int] = []
    spend_series: list[int] = []
    now = _now()
    for i in range(months - 1, -1, -1):
        ref = now - timedelta(days=30 * i)
        start = datetime(ref.year, ref.month, 1)
        if ref.month == 12:
            end = datetime(ref.year + 1, 1, 1)
        else:
            end = datetime(ref.year, ref.month + 1, 1)
        labels.append(start.strftime("%b %Y"))
        cnt = (
            db.query(func.count(Order.id))
            .filter(Order.merchant_id == merchant_id, Order.created_at >= start, Order.created_at < end)
            .scalar()
            or 0
        )
        spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == merchant_id,
                Order.created_at >= start,
                Order.created_at < end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .scalar()
            or 0
        )
        orders_series.append(int(cnt))
        spend_series.append(int(spend))
    return {"labels": labels, "orders": orders_series, "spend_cents": spend_series}


def daily_volume(db: Session, merchant_id: str, days: int = 7) -> dict[str, list[dict[str, Any]]]:
    now = _now()
    daily_orders: list[dict[str, Any]] = []
    daily_spend: list[dict[str, Any]] = []
    for offset in range(days - 1, -1, -1):
        day = datetime.combine((now - timedelta(days=offset)).date(), datetime.min.time())
        day_end = day + timedelta(days=1)
        label = day.strftime("%a")
        count = (
            db.query(func.count(Order.id))
            .filter(Order.merchant_id == merchant_id, Order.created_at >= day, Order.created_at < day_end)
            .scalar()
            or 0
        )
        spend = (
            db.query(func.coalesce(func.sum(Order.amount_cents), 0))
            .filter(
                Order.merchant_id == merchant_id,
                Order.created_at >= day,
                Order.created_at < day_end,
                Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
            )
            .scalar()
            or 0
        )
        daily_orders.append({"label": label, "value": int(count)})
        daily_spend.append({"label": label, "value": int(spend)})
    return {"daily_orders": daily_orders, "daily_spend_cents": daily_spend}


def _as_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def promised_at(order: Order) -> datetime | None:
    return _as_naive_utc(delivery_window_end(order.compliance_metadata) or order.scheduled_at)


def delivered_event_at(db: Session, orders: list[Order]) -> dict[str, datetime]:
    ids = [order.id for order in orders]
    if not ids:
        return {}
    events = (
        db.query(OrderEvent)
        .filter(OrderEvent.order_id.in_(ids), OrderEvent.event_type == "order.delivered")
        .order_by(OrderEvent.occurred_at.asc())
        .all()
    )
    latest: dict[str, datetime] = {}
    for ev in events:
        ts = _as_naive_utc(ev.occurred_at)
        if ts is None:
            continue
        latest[ev.order_id] = ts
    return latest


def score_on_time(db: Session, orders: list[Order]) -> dict[str, Any]:
    """On-time only when a promised time and a delivered event both exist."""
    delivered_at = delivered_event_at(db, orders)
    grace = timedelta(minutes=ON_TIME_GRACE_MINUTES)
    on_time = 0
    sample = 0
    for order in orders:
        target = promised_at(order)
        actual = delivered_at.get(order.id)
        if target is None or actual is None:
            continue
        sample += 1
        if actual <= target + grace:
            on_time += 1
    return {
        "on_time_orders": on_time,
        "on_time_sample_size": sample,
        "on_time_percent": round((on_time / sample * 100), 1) if sample else None,
        "grace_minutes": ON_TIME_GRACE_MINUTES,
    }


def period_meta(since: datetime | None = None) -> dict[str, Any]:
    start = since or month_start()
    return {
        "label": start.strftime("%B %Y"),
        "since": start.isoformat(),
        "timezone": "UTC",
        "note": "Calendar month in UTC. On-time needs a promised time and a delivered event.",
    }


def delivery_performance(db: Session, merchant_id: str, *, since: datetime | None = None) -> dict[str, Any]:
    since = since or month_start()
    total = (
        db.query(func.count(Order.id))
        .filter(Order.merchant_id == merchant_id, Order.created_at >= since)
        .scalar()
        or 0
    )
    delivered_orders = (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
            Order.state.in_(DONE_STATES),
        )
        .all()
    )
    delivered = len(delivered_orders)
    failed = (
        db.query(func.count(Order.id))
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
            Order.state.in_(FAILED_STATES),
        )
        .scalar()
        or 0
    )
    returned = (
        db.query(func.count(Order.id))
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
            Order.state.in_(RETURNED_STATES),
        )
        .scalar()
        or 0
    )
    scored = score_on_time(db, delivered_orders)
    on_time_pct = scored["on_time_percent"]
    return {
        "total_orders": int(total),
        "delivered": int(delivered),
        "failed_deliveries": int(failed),
        "returned": int(returned),
        "on_time_percent": on_time_pct,
        "on_time_orders": scored["on_time_orders"],
        "on_time_sample_size": scored["on_time_sample_size"],
        "grace_minutes": scored["grace_minutes"],
        "delivery_success_percent": round((delivered / total * 100), 1) if total else None,
        "failed_percent": round((failed / total * 100), 1) if total else None,
        "sla_percent": on_time_pct,
        "avg_pickup_hours": merchant_avg_duration_hours(
            db, merchant_id, "order.driver_assigned", "order.picked_up", since=since
        ),
        "avg_delivery_hours": merchant_avg_duration_hours(
            db, merchant_id, "order.picked_up", "order.delivered", since=since
        ),
        "period": period_meta(since),
    }


def order_export_rows(db: Session, merchant_id: str, *, since: datetime | None = None, limit: int = 500) -> list[dict[str, Any]]:
    since = since or month_start()
    rows = (
        db.query(Order)
        .filter(Order.merchant_id == merchant_id, Order.created_at >= since)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "order_number": order.order_number,
            "tracking_number": order.tracking_number,
            "state": order.state,
            "amount_cents": order.amount_cents,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }
        for order in rows
    ]


def top_destinations(db: Session, merchant_id: str, *, since: datetime | None = None, limit: int = 10) -> list[dict[str, Any]]:
    since = since or month_start()
    destinations: dict[str, int] = {}
    orders = (
        db.query(Order)
        .filter(Order.merchant_id == merchant_id, Order.created_at >= since)
        .limit(1000)
        .all()
    )
    for order in orders:
        drop = order.dropoff if isinstance(order.dropoff, dict) else {}
        label = str(drop.get("formatted") or drop.get("city") or "Unknown")
        destinations[label] = destinations.get(label, 0) + 1
    return sorted(
        [{"destination": k, "count": v} for k, v in destinations.items()],
        key=lambda x: x["count"],
        reverse=True,
    )[:limit]


def top_routes(db: Session, merchant_id: str, *, since: datetime | None = None, limit: int = 10) -> list[dict[str, Any]]:
    since = since or month_start()
    routes: dict[str, int] = {}
    for order in db.query(Order).filter(Order.merchant_id == merchant_id, Order.created_at >= since).limit(1000):
        pickup = order.pickup if isinstance(order.pickup, dict) else {}
        drop = order.dropoff if isinstance(order.dropoff, dict) else {}
        key = f"{pickup.get('formatted', '?')} → {drop.get('formatted', '?')}"
        routes[key] = routes.get(key, 0) + 1
    return sorted([{"route": k, "count": v} for k, v in routes.items()], key=lambda x: x["count"], reverse=True)[:limit]


def driver_performance(db: Session, merchant_id: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    since = since or month_start()
    drivers = {d.id: d for d in db.query(Driver).all()}
    counts: dict[str, dict[str, Any]] = {}
    for order in db.query(Order).filter(
        Order.merchant_id == merchant_id,
        Order.created_at >= since,
        Order.assigned_driver_id.isnot(None),
    ):
        did = order.assigned_driver_id
        if not did:
            continue
        bucket = counts.setdefault(
            did,
            {
                "driver_id": did,
                "name": drivers[did].full_name if did in drivers else did,
                "orders": 0,
                "delivered": 0,
                "failed": 0,
            },
        )
        bucket["orders"] += 1
        if order.state in DONE_STATES:
            bucket["delivered"] += 1
        if order.state in FAILED_STATES:
            bucket["failed"] += 1
    rows = list(counts.values())
    for row in rows:
        total = row["orders"] or 1
        row["success_percent"] = round(row["delivered"] / total * 100, 1)
    return sorted(rows, key=lambda x: x["orders"], reverse=True)[:15]


def vehicle_usage(db: Session, merchant_id: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    since = since or month_start()
    vehicles = {v.id: v for v in db.query(Vehicle).all()}
    driver_vehicle: dict[str, str] = {}
    for v in db.query(Vehicle).filter(Vehicle.is_active.is_(True)):
        if v.driver_id:
            driver_vehicle[v.driver_id] = v.id
    usage: dict[str, dict[str, Any]] = {}
    for order in db.query(Order).filter(
        Order.merchant_id == merchant_id,
        Order.created_at >= since,
        Order.assigned_driver_id.isnot(None),
    ):
        vid = driver_vehicle.get(order.assigned_driver_id or "")
        if not vid:
            continue
        vehicle = vehicles.get(vid)
        bucket = usage.setdefault(
            vid,
            {
                "vehicle_id": vid,
                "label": f"{vehicle.make_model or vehicle.vehicle_class} ({vehicle.plate_number})"
                if vehicle
                else vid,
                "vehicle_class": vehicle.vehicle_class if vehicle else None,
                "orders": 0,
            },
        )
        bucket["orders"] += 1
    return sorted(usage.values(), key=lambda x: x["orders"], reverse=True)[:15]


def claims_summary(db: Session, merchant_id: str, *, since: datetime | None = None) -> dict[str, Any]:
    since = since or month_start()
    claims = (
        db.query(Claim)
        .join(Order, Claim.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Claim.created_at >= since)
        .all()
    )
    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    compensation = 0
    for claim in claims:
        by_type[claim.claim_type] = by_type.get(claim.claim_type, 0) + 1
        by_status[claim.status] = by_status.get(claim.status, 0) + 1
        comp = (claim.resolution or {}).get("compensation") or {}
        compensation += int(comp.get("approved_amount_cents") or 0)
    return {
        "total_claims": len(claims),
        "open_claims": sum(1 for c in claims if c.status in ("open", "investigating")),
        "by_type": by_type,
        "by_status": by_status,
        "compensation_cost_cents": compensation,
    }


def invoice_summary(db: Session, merchant_id: str, *, since: datetime | None = None) -> dict[str, Any]:
    since = since or month_start()
    rows = (
        db.query(Invoice, Order)
        .join(Order, Invoice.order_id == Order.id)
        .filter(Order.merchant_id == merchant_id, Invoice.created_at >= since)
        .all()
    )
    total = sum(inv.amount_cents for inv, _ in rows)
    tax = sum(inv.tax_cents for inv, _ in rows)
    return {
        "invoice_count": len(rows),
        "invoice_total_cents": int(total),
        "tax_cents": int(tax),
        "currency": rows[0][0].currency if rows else "cad",
    }


def channel_for_order_source(order_source: str | None) -> str:
    """Map Order.order_source → report channel (shopify | portal | api | other)."""
    src = (order_source or "").upper()
    if src == "SHOPIFY":
        return "shopify"
    if src == "API":
        return "api"
    if src in ("MERCHANT", "CSV", "ADMIN", "PHONE", "PARTNER"):
        return "portal"
    if src == "WEBSITE":
        return "website"
    return "other"


def _spendable_orders(db: Session, merchant_id: str, *, since: datetime | None = None):
    since = since or month_start()
    return (
        db.query(Order)
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
            Order.state.notin_([OrderState.CANCELLED.value, OrderState.REFUNDED.value]),
        )
        .all()
    )


def spend_by_channel(db: Session, merchant_id: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    """Operational spend attributed by booking channel (Quote≡Book≡Report)."""
    buckets: dict[str, dict[str, int]] = {}
    for order in _spendable_orders(db, merchant_id, since=since):
        channel = channel_for_order_source(order.order_source)
        row = buckets.setdefault(channel, {"orders": 0, "spend_cents": 0})
        row["orders"] += 1
        row["spend_cents"] += int(order.amount_cents or 0)
    preferred = ("shopify", "portal", "api", "website", "other")
    out = [
        {"channel": ch, "orders": buckets[ch]["orders"], "spend_cents": buckets[ch]["spend_cents"]}
        for ch in preferred
        if ch in buckets
    ]
    for ch, data in sorted(buckets.items()):
        if ch not in preferred:
            out.append({"channel": ch, "orders": data["orders"], "spend_cents": data["spend_cents"]})
    return out


def spend_by_pricing_model(db: Session, merchant_id: str, *, since: datetime | None = None) -> list[dict[str, Any]]:
    """Spend under the merchant's pricing model (fsa | distance)."""
    from porterchain_api.merchant_models import Merchant

    merchant = db.get(Merchant, merchant_id)
    model = (getattr(merchant, "pricing_model", None) or "distance").lower()
    if model not in ("fsa", "distance"):
        model = "distance"
    orders = _spendable_orders(db, merchant_id, since=since)
    spend = sum(int(o.amount_cents or 0) for o in orders)
    return [{"pricing_model": model, "orders": len(orders), "spend_cents": spend}]


def _fsa_from_dropoff(dropoff: Any) -> str | None:
    if not isinstance(dropoff, dict):
        return None
    for key in ("postal_code", "postal", "zip", "fsa"):
        raw = dropoff.get(key)
        if not raw:
            continue
        cleaned = "".join(ch for ch in str(raw).upper() if ch.isalnum())
        if len(cleaned) >= 3:
            return cleaned[:3]
    formatted = str(dropoff.get("formatted") or "")
    for token in formatted.upper().replace(",", " ").split():
        cleaned = "".join(ch for ch in token if ch.isalnum())
        if len(cleaned) >= 3 and cleaned[0].isalpha() and cleaned[1].isdigit():
            return cleaned[:3]
    return None


def _distance_band_label(meters: int | None) -> str:
    if meters is None or meters < 0:
        return "unknown"
    km = meters / 1000.0
    if km < 5:
        return "0–5 km"
    if km < 10:
        return "5–10 km"
    if km < 20:
        return "10–20 km"
    if km < 40:
        return "20–40 km"
    return "40+ km"


def top_pricing_bands(
    db: Session,
    merchant_id: str,
    *,
    since: datetime | None = None,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Top FSA codes (fsa model) or distance bands (distance model) by spend."""
    from porterchain_api.merchant_models import Merchant

    merchant = db.get(Merchant, merchant_id)
    model = (getattr(merchant, "pricing_model", None) or "distance").lower()
    buckets: dict[str, dict[str, int]] = {}
    for order in _spendable_orders(db, merchant_id, since=since):
        if model == "fsa":
            band = _fsa_from_dropoff(order.dropoff) or "unknown"
        else:
            meters = None
            compliance = order.compliance_metadata if isinstance(order.compliance_metadata, dict) else {}
            quote = compliance.get("quote") if isinstance(compliance.get("quote"), dict) else {}
            if quote.get("distance_meters") is not None:
                try:
                    meters = int(quote["distance_meters"])
                except (TypeError, ValueError):
                    meters = None
            band = _distance_band_label(meters)
        row = buckets.setdefault(band, {"orders": 0, "spend_cents": 0})
        row["orders"] += 1
        row["spend_cents"] += int(order.amount_cents or 0)
    ranked = sorted(buckets.items(), key=lambda kv: (-kv[1]["spend_cents"], kv[0]))[:limit]
    return [
        {
            "band": name,
            "pricing_model": model if model in ("fsa", "distance") else "distance",
            "orders": data["orders"],
            "spend_cents": data["spend_cents"],
        }
        for name, data in ranked
    ]


def spend_attribution(db: Session, merchant_id: str, *, since: datetime | None = None) -> dict[str, Any]:
    since = since or month_start()
    return {
        "by_channel": spend_by_channel(db, merchant_id, since=since),
        "by_pricing_model": spend_by_pricing_model(db, merchant_id, since=since),
        "top_bands": top_pricing_bands(db, merchant_id, since=since),
        "period": period_meta(since),
    }


def rows_to_csv(rows: list[dict[str, Any]], fieldnames: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buffer.getvalue()


def rows_to_excel(rows: list[dict[str, Any]], fieldnames: list[str], sheet_name: str = "Report") -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as exc:
        raise ValueError("excel_support_unavailable") from exc
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name[:31]
    ws.append(fieldnames)
    for row in rows:
        ws.append([row.get(k, "") for k in fieldnames])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()
