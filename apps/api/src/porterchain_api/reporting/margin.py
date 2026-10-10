"""Real margin per stop and per route: revenue (pre-tax) − driver cost − Stripe fee.

* Revenue: the pre-tax amount on the invoice line (cycle invoices) or the invoice
  (amount − tax); for an order not invoiced yet, the order price with tax taken out.
* Driver cost: what the driver was actually credited for that delivery (wallet
  ``delivery`` transactions). When nothing is recorded yet, the super-admin driver pay
  plan ($27/h hourly, wave blocks, per stop…) is applied to an estimated time
  (finance setting ``margin_minutes_per_stop``) and the row says ``estimate``.
* Route: one driver on one day (the same grouping driver earnings already use).
* Anything under ``margin_floor_pct`` is flagged.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.billing_engine.models import BillingLedgerEntry, InvoiceLine
from porterchain_api.booking_models import Invoice, Order
from porterchain_api.driver_models import DriverWalletTransaction


def _plan(db: Session) -> dict[str, Any]:
    from porterchain_pricing.driver_pay import default_driver_pay_plan, normalize_driver_pay_plan

    from porterchain_api.merchant_engine.config_read import config_dict

    raw = config_dict(db, "driver_pay_plan") or {}
    try:
        return normalize_driver_pay_plan({**default_driver_pay_plan(), **raw})
    except ValueError:
        return default_driver_pay_plan()


def _estimate(plan: dict[str, Any], *, stops: int, minutes: float) -> int:
    from porterchain_pricing.driver_pay import compute_driver_pay

    return int(compute_driver_pay(plan, paid_minutes=minutes, stops=stops, routes=1, blocks=0).total_cents)


def _pct(margin: int, revenue: int) -> float | None:
    return round(margin * 100.0 / revenue, 1) if revenue else None


def margin_report(
    db: Session, *, days: int = 30, now: datetime | None = None, merchant_id: str | None = None
) -> dict[str, Any]:
    from porterchain_api.admin_engine.platform_settings import finance_number
    from porterchain_api.order_engine.buckets import DONE_STATES
    from porterchain_api.platform.merchant_billing import charged_tax_split

    now = now or datetime.now(UTC)
    since = now - timedelta(days=max(1, min(days, 366)))
    floor = finance_number(db, "margin_floor_pct", 25.0)
    minutes = finance_number(db, "margin_minutes_per_stop", 30.0)
    plan = _plan(db)

    q = db.query(Order).filter(
        Order.state.in_(DONE_STATES),
        Order.is_sandbox.is_(False),
        Order.scheduled_at >= since,
        Order.scheduled_at <= now,
    )
    if merchant_id:
        q = q.filter(Order.merchant_id == merchant_id)
    orders = q.order_by(Order.scheduled_at.asc()).limit(5000).all()
    ids = [o.id for o in orders]

    line_rev = {
        ln.order_id: int(ln.amount_cents or 0)
        for ln in db.query(InvoiceLine).filter(InvoiceLine.order_id.in_(ids)).all()
    } if ids else {}
    inv_rev = {
        inv.order_id: int(inv.amount_cents or 0) - int(inv.tax_cents or 0)
        for inv in db.query(Invoice).filter(Invoice.order_id.in_(ids)).all()
    } if ids else {}
    pay: dict[str, int] = defaultdict(int)
    for t in (
        db.query(DriverWalletTransaction)
        .filter(DriverWalletTransaction.tx_type == "delivery", DriverWalletTransaction.reference_id.in_(ids))
        .all()
        if ids
        else []
    ):
        pay[t.reference_id] += int(t.amount_cents or 0)
    fees: dict[str, int] = defaultdict(int)
    for f in (
        db.query(BillingLedgerEntry)
        .filter(BillingLedgerEntry.kind == "stripe_fee", BillingLedgerEntry.order_id.in_(ids))
        .all()
        if ids
        else []
    ):
        fees[f.order_id] += int(f.amount_cents or 0)

    # A single stop costs its share of driver time (route minimums are charged per route).
    if plan.get("mode") == "per_stop":
        per_stop_estimate = int(plan.get("per_stop_cents") or 0)
    else:
        per_stop_estimate = int(round(int(plan.get("hourly_cents") or 2700) * minutes / 60.0))
    stops: list[dict[str, Any]] = []
    routes: dict[tuple[str, str], dict[str, Any]] = {}
    for o in orders:
        if o.id in line_rev:
            revenue = line_rev[o.id]
        elif o.id in inv_rev:
            revenue = inv_rev[o.id]
        else:
            revenue = charged_tax_split(db, o, int(o.amount_cents or 0)).pretax_cents
        actual = o.id in pay
        cost = pay[o.id] if actual else per_stop_estimate
        fee = fees.get(o.id, 0)
        margin = revenue - cost - fee
        pct = _pct(margin, revenue)
        day = (o.scheduled_at or now).date().isoformat()
        stops.append(
            {
                "order_id": o.id,
                "order_number": o.order_number,
                "merchant_id": o.merchant_id,
                "driver_id": o.assigned_driver_id,
                "day": day,
                "revenue_cents": revenue,
                "driver_cost_cents": cost,
                "stripe_fee_cents": fee,
                "margin_cents": margin,
                "margin_pct": pct,
                "cost_source": "actual" if actual else "estimate",
                "below_floor": pct is not None and pct < floor,
            }
        )
        if o.assigned_driver_id:
            key = (o.assigned_driver_id, day)
            r = routes.setdefault(
                key,
                {"route_id": f"{day}:{o.assigned_driver_id}", "driver_id": o.assigned_driver_id, "day": day,
                 "stops": 0, "revenue_cents": 0, "actual_cost_cents": 0, "actual_stops": 0, "stripe_fee_cents": 0},
            )
            r["stops"] += 1
            r["revenue_cents"] += revenue
            r["stripe_fee_cents"] += fee
            if actual:
                r["actual_cost_cents"] += cost
                r["actual_stops"] += 1

    route_rows = []
    for r in routes.values():
        if r["actual_stops"] == r["stops"]:
            cost, source = r["actual_cost_cents"], "actual"
        else:
            # The pay plan decides route cost (e.g. a 4 h wave block is paid even for 2 stops).
            cost, source = _estimate(plan, stops=r["stops"], minutes=minutes * r["stops"]), "estimate"
        margin = r["revenue_cents"] - cost - r["stripe_fee_cents"]
        pct = _pct(margin, r["revenue_cents"])
        route_rows.append(
            {
                **{k: r[k] for k in ("route_id", "driver_id", "day", "stops", "revenue_cents", "stripe_fee_cents")},
                "driver_cost_cents": cost,
                "margin_cents": margin,
                "margin_pct": pct,
                "cost_source": source,
                "below_floor": pct is not None and pct < floor,
            }
        )
    route_rows.sort(key=lambda r: (r["margin_pct"] if r["margin_pct"] is not None else 999))
    stops.sort(key=lambda r: (r["margin_pct"] if r["margin_pct"] is not None else 999))

    revenue = sum(s["revenue_cents"] for s in stops)
    driver_cost = sum(r["driver_cost_cents"] for r in route_rows) + sum(
        s["driver_cost_cents"] for s in stops if not s["driver_id"]
    )
    fee_total = sum(s["stripe_fee_cents"] for s in stops)
    margin_total = revenue - driver_cost - fee_total
    return {
        "days": days,
        "floor_pct": floor,
        "pay_mode": plan.get("mode"),
        "hourly_cents": plan.get("hourly_cents"),
        "minutes_per_stop": minutes,
        "totals": {
            "stops": len(stops),
            "routes": len(route_rows),
            "revenue_cents": revenue,
            "driver_cost_cents": driver_cost,
            "stripe_fee_cents": fee_total,
            "margin_cents": margin_total,
            "margin_pct": _pct(margin_total, revenue),
            "stops_below_floor": sum(1 for s in stops if s["below_floor"]),
            "routes_below_floor": sum(1 for r in route_rows if r["below_floor"]),
            "estimated_share": round(sum(1 for s in stops if s["cost_source"] == "estimate") / len(stops), 2)
            if stops
            else 0.0,
        },
        "routes": route_rows[:200],
        "stops": stops[:500],
    }
