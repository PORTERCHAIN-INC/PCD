"""Waiting-time and failed-delivery fees for merchant cycle invoices, from recorded evidence.

Waiting: driver check-ins at each stop (``arrived`` -> ``picked_up``/``delivered``/``failed``)
with the carriage terms allowance (15 min free per pickup and per stop, then $30/hr in
15-minute increments, editable in Settings > Carriage terms or per contract).
Failed delivery: orders that ended FAILED / RETURN_TO_SENDER, charged the return fee
(% of the stop price). Each fee is its own invoice line whose description carries the
evidence (times, minutes, status) and the same evidence is stamped on the order.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from porterchain_pricing.contract_terms import failed_delivery_cents, terms_of, waiting_cents

_TZ = ZoneInfo("America/Toronto")
FAILED_STATES = ("FAILED", "RETURN_TO_SENDER")
_DONE = {"picked_up", "delivered", "failed"}


@dataclass
class Accessorial:
    order: Any
    code: str  # waiting | failed_delivery
    description: str
    amount_cents: int
    evidence: dict[str, Any] = field(default_factory=dict)


def merchant_terms(db: Session, merchant: Any) -> dict[str, Any]:
    from porterchain_api.admin_models import SystemConfig
    from porterchain_pricing.contract_schedule import load_contract_schedule

    row = db.get(SystemConfig, "carriage_terms")
    global_terms = row.value if row is not None and isinstance(row.value, dict) else None
    sched = ((merchant.pricing_config or {}).get("schedule") or {}) if merchant else {}
    sid = sched.get("contract_schedule")
    schedule = load_contract_schedule(sid, sched.get("contract_overrides")) if sid else None
    return terms_of(schedule, global_terms)


def _hm(at: datetime) -> str:
    return at.astimezone(_TZ).strftime("%b %d %H:%M")


def stop_waits(events: list[tuple[str, str, datetime]]) -> list[dict[str, Any]]:
    """``(stop_key, event, at)`` -> per stop: kind, arrived, done, minutes on site."""
    arrived: dict[str, datetime] = {}
    done: dict[str, datetime] = {}
    for key, ev, at in events:
        if ev == "arrived":
            arrived[key] = min(at, arrived.get(key, at))
        elif ev in _DONE:
            done[key] = max(at, done.get(key, at))
    out = []
    for key, a in arrived.items():
        d = done.get(key)
        if d is None or d <= a:
            continue
        kind = "pickup" if ":p" in key or key.endswith(":pickup") else "drop"
        out.append({"stop_key": key, "kind": kind, "arrived": a, "done": d,
                    "minutes": round((d - a).total_seconds() / 60, 1)})
    return sorted(out, key=lambda s: s["arrived"])


def waiting_for(order: Any, events: list[tuple[str, str, datetime]], terms: dict[str, Any]) -> Accessorial | None:
    stops = stop_waits(events)
    if not stops:
        return None
    pickup = sum(s["minutes"] for s in stops if s["kind"] == "pickup")
    drops = [s["minutes"] for s in stops if s["kind"] == "drop"]
    calc = waiting_cents(terms, pickup_minutes=pickup, stop_minutes=drops)
    if not calc["total_cents"]:
        return None
    w = terms["waiting"]
    parts = [f"{s['kind']} {_hm(s['arrived'])}-{s['done'].astimezone(_TZ).strftime('%H:%M')} ({s['minutes']:g} min)"
             for s in stops]
    desc = (f"Waiting time {order.order_number}: " + "; ".join(parts)
            + f" · {w['stop_included_minutes']} min free, ${w['cents_per_hour'] / 100:g}/hr")
    evidence = {"stops": [{**s, "arrived": s["arrived"].isoformat(), "done": s["done"].isoformat()} for s in stops],
                "lines": calc["lines"], "source": "driver check-ins"}
    return Accessorial(order, "waiting", desc[:255], int(calc["total_cents"]), evidence)


def failed_for(order: Any, terms: dict[str, Any], failed_at: datetime | None) -> Accessorial | None:
    stop_rate = int(order.amount_cents or 0)
    if stop_rate <= 0:
        return None
    meta = order.compliance_metadata or {}
    vehicle = str((meta.get("analytics") or {}).get("vehicle") or meta.get("vehicle_class") or "")
    kind = "compact" if vehicle in {"compact", "sedan", "car", "hatchback"} else "van"
    cents = failed_delivery_cents(terms, vehicle=kind, stop_rate_cents=stop_rate)
    if cents <= 0:
        return None
    pct = terms["failed_delivery"]["compact_pct" if kind == "compact" else "van_pct"]
    when = f" at {_hm(failed_at)}" if failed_at else ""
    reason = str(meta.get("failure_reason") or meta.get("failed_reason") or "").strip()
    desc = (f"Failed delivery {order.order_number}: status {order.state}{when}"
            + (f" ({reason})" if reason else "") + f" · return fee {pct}% of ${stop_rate / 100:.2f}")
    evidence = {"state": order.state, "failed_at": failed_at.isoformat() if failed_at else None,
                "reason": reason or None, "stop_rate_cents": stop_rate, "pct": pct, "vehicle": kind,
                "source": "order status + driver check-in"}
    return Accessorial(order, "failed_delivery", desc[:255], int(cents), evidence)


def accessorial_lines(db: Session, merchant: Any, delivered: list[Any]) -> list[Accessorial]:
    """Fees for this invoice: waiting on the delivered orders, failed fees on failed ones."""
    from porterchain_api.billing_engine.models import InvoiceLine
    from porterchain_api.booking_models import Order
    from porterchain_api.platform.stop_evidence import stop_events_by_order

    terms = merchant_terms(db, merchant)
    invoiced_ids = {r[0] for r in db.query(InvoiceLine.order_id).join(Order, Order.id == InvoiceLine.order_id)
                    .filter(Order.merchant_id == merchant.id, Order.state.in_(FAILED_STATES)).all()}
    failed = [o for o in db.query(Order).filter(Order.merchant_id == merchant.id,
                                                Order.state.in_(FAILED_STATES)).all()
              if o.id not in invoiced_ids and not o.is_sandbox]
    by_order = stop_events_by_order(db, [o.id for o in [*delivered, *failed]])
    out: list[Accessorial] = []
    for o in delivered:
        a = waiting_for(o, by_order.get(o.id, []), terms)
        if a:
            out.append(a)
    for o in failed:
        fails = [at for _k, ev, at in by_order.get(o.id, []) if ev == "failed"]
        a = failed_for(o, terms, max(fails) if fails else o.updated_at)
        if a:
            out.append(a)
    return out


def stamp(order: Any, acc: Accessorial, invoice_id: str) -> None:
    """Evidence on the order so the merchant can see why (portal order detail)."""
    meta = dict(order.compliance_metadata or {})
    rows = [r for r in (meta.get("accessorials") or []) if r.get("code") != acc.code]
    rows.append({"code": acc.code, "amount_cents": acc.amount_cents, "invoice_id": invoice_id,
                 "description": acc.description, "evidence": acc.evidence})
    meta["accessorials"] = rows
    order.compliance_metadata = meta


def fee_tax_split(db: Session, order: Any, cents: int) -> Any:
    """Fees are pre-tax amounts; HST/GST by the order's destination province."""
    from porterchain_api.billing_engine.tax import _settings, order_province, split_amount

    _mode, default_prov, qst = _settings(db)
    return split_amount(cents, province=order_province(order, default_prov), mode="exclusive", collect_qst=qst)


def fee_specs(db: Session, merchant: Any, delivered: list[Any]) -> list[tuple[Accessorial, Any]]:
    return [(x, fee_tax_split(db, x.order, x.amount_cents)) for x in accessorial_lines(db, merchant, delivered)]


def add_fee_lines(db: Session, invoice_id: str, specs: list[tuple[Accessorial, Any]]) -> None:
    """One invoice line per fee (evidence in the text) and the evidence stamped on the order."""
    from porterchain_api.billing_engine.models import InvoiceLine

    for x, split in specs:
        db.add(InvoiceLine(invoice_id=invoice_id, order_id=x.order.id, description=x.description,
                           amount_cents=split.pretax_cents, tax_cents=split.tax_cents, tax_province=split.province))
        stamp(x.order, x, invoice_id)
