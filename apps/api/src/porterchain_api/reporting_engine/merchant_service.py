"""Merchant reporting engine — SQL aggregates scoped to merchant (masterrule §11)."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.order_engine.buckets import DONE_STATES, FAILED_STATES
from porterchain_api.admin_models import Claim, Driver, Vehicle
from porterchain_api.domain.states import OrderState
from porterchain_api.models import Invoice, Order, OrderEvent

RETURNED_STATES = ("RETURN_TO_SENDER",)

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
) -> float:
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
    return round(sum(deltas) / len(deltas), 1) if deltas else 0.0


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


def delivery_performance(db: Session, merchant_id: str, *, since: datetime | None = None) -> dict[str, Any]:
    since = since or month_start()
    total = (
        db.query(func.count(Order.id))
        .filter(Order.merchant_id == merchant_id, Order.created_at >= since)
        .scalar()
        or 0
    )
    delivered = (
        db.query(func.count(Order.id))
        .filter(
            Order.merchant_id == merchant_id,
            Order.created_at >= since,
            Order.state.in_(DONE_STATES),
        )
        .scalar()
        or 0
    )
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
    on_time = delivered  # SLA proxy: delivered within period
    return {
        "total_orders": int(total),
        "delivered": int(delivered),
        "failed_deliveries": int(failed),
        "returned": int(returned),
        "on_time_percent": round((on_time / total * 100) if total else 100.0, 1),
        "delivery_success_percent": round((delivered / total * 100) if total else 100.0, 1),
        "failed_percent": round((failed / total * 100) if total else 0.0, 1),
        "sla_percent": round((on_time / total * 100) if total else 100.0, 1),
        "avg_pickup_hours": merchant_avg_duration_hours(
            db, merchant_id, "order.driver_assigned", "order.picked_up", since=since
        ),
        "avg_delivery_hours": merchant_avg_duration_hours(
            db, merchant_id, "order.picked_up", "order.delivered", since=since
        ),
    }


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
