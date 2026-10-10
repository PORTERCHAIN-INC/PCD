"""Signed-in customer: Orders, address book, autofill, report a problem."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import (
    Customer,
    CustomerAddress,
    Invoice,
    Order,
    OrderRating,
)
from porterchain_api.config import Settings
from porterchain_api.customer_fast import geo, rules, service

MAX_SAVED = 30
PROBLEM_KINDS = {
    "late": "Late or missed pickup / delivery",
    "damaged": "Item damaged",
    "missing": "Item missing",
    "wrong_address": "Delivered to the wrong place",
    "return": "Return this delivery to sender",
    "billing": "Billing question",
    "other": "Something else",
}
ACTIVE_STATES = {
    "BOOKED", "DISPATCH_READY", "DRIVER_ASSIGNED", "DRIVER_ACCEPTED", "DRIVER_EN_ROUTE",
    "AT_PICKUP", "PICKED_UP", "IN_TRANSIT", "AT_DESTINATION",
}


def _now() -> datetime:
    return datetime.now(UTC)


# --------------------------------------------------------------------------- address book


def _addr_out(a: CustomerAddress) -> dict[str, Any]:
    return {
        "id": a.id,
        "label": a.label,
        "formatted": a.formatted,
        "postal": a.postal,
        "lat": a.lat,
        "lng": a.lng,
        "place_id": a.place_id,
        "contact_name": a.contact_name,
        "phone": a.phone,
        "saved": bool(a.saved),
        "use_count": a.use_count or 0,
    }


def learn_address(db: Session, customer_id: str, addr: dict[str, Any] | None) -> CustomerAddress | None:
    """Record one use of an address (history → autofill). Never overwrites a saved label."""
    key = rules.address_key(addr)
    if not key or not isinstance(addr, dict):
        return None
    row = (
        db.query(CustomerAddress)
        .filter(CustomerAddress.customer_id == customer_id, CustomerAddress.address_key == key)
        .first()
    )
    filled = geo.with_coords(addr) or {}
    if row is None:
        row = CustomerAddress(
            customer_id=customer_id,
            address_key=key,
            formatted=str(addr.get("formatted") or "")[:512],
            postal=geo.postal_of(addr),
            lat=filled.get("lat"),
            lng=filled.get("lng"),
            place_id=addr.get("place_id"),
            contact_name=addr.get("contact_name"),
            phone=addr.get("phone"),
            saved=False,
            use_count=0,
        )
        db.add(row)
    row.use_count = (row.use_count or 0) + 1
    row.last_used_at = _now()
    return row


def learn_from_history(db: Session, customer: Customer) -> None:
    """Backfill the book from past orders once (cheap: only when the book is empty)."""
    if db.query(CustomerAddress.id).filter(CustomerAddress.customer_id == customer.id).first():
        return
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id, Order.merchant_id.is_(None))
        .order_by(Order.created_at.desc())
        .limit(25)
        .all()
    )
    for o in orders:
        learn_address(db, customer.id, o.pickup)
        learn_address(db, customer.id, o.dropoff)
        db.flush()


def list_addresses(db: Session, customer: Customer) -> list[dict[str, Any]]:
    learn_from_history(db, customer)
    db.commit()
    rows = (
        db.query(CustomerAddress)
        .filter(CustomerAddress.customer_id == customer.id)
        .order_by(CustomerAddress.saved.desc(), CustomerAddress.use_count.desc(), CustomerAddress.last_used_at.desc())
        .limit(MAX_SAVED)
        .all()
    )
    return [_addr_out(a) for a in rows]


def suggestions(db: Session, customer: Customer, q: str | None = None, limit: int = 5) -> list[dict[str, Any]]:
    """Autofill: saved first, then most-used, filtered by what the user typed."""
    items = list_addresses(db, customer)
    needle = " ".join((q or "").lower().split())
    if needle:
        items = [a for a in items if needle in (a["formatted"] or "").lower() or needle in (a["label"] or "").lower()]
    return items[: max(1, min(limit, 10))]


def save_address(db: Session, customer: Customer, data: dict[str, Any]) -> dict[str, Any]:
    formatted = str(data.get("formatted") or "").strip()
    if len(formatted) < 5:
        raise ValueError("address_invalid")
    saved_count = (
        db.query(CustomerAddress)
        .filter(CustomerAddress.customer_id == customer.id, CustomerAddress.saved.is_(True))
        .count()
    )
    row = learn_address(db, customer.id, {**data, "formatted": formatted})
    if row is None:
        raise ValueError("address_invalid")
    if not row.saved and saved_count >= MAX_SAVED:
        raise ValueError("address_book_full")
    row.use_count = max(0, (row.use_count or 1) - 1)  # saving is not a use
    row.saved = True
    if data.get("label") is not None:
        row.label = str(data["label"]).strip()[:64] or None
    for field in ("contact_name", "phone"):
        if data.get(field) is not None:
            setattr(row, field, str(data[field]).strip()[:255] or None)
    db.commit()
    return _addr_out(row)


def delete_address(db: Session, customer: Customer, address_id: str) -> None:
    row = db.get(CustomerAddress, address_id)
    if row is None or row.customer_id != customer.id:
        raise ValueError("address_not_found")
    db.delete(row)
    db.commit()


# --------------------------------------------------------------------------- orders


def _stops(order: Order) -> list[dict[str, Any]]:
    quote = order.quote
    extra = quote.additional_stops if quote is not None and isinstance(quote.additional_stops, list) else []
    return [s for s in extra if isinstance(s, dict)]


def my_orders(db: Session, settings: Settings, customer: Customer, limit: int = 50) -> dict[str, Any]:
    orders = (
        db.query(Order)
        .filter(Order.customer_id == customer.id, Order.is_sandbox.is_(False))
        .order_by(Order.created_at.desc())
        .limit(max(1, min(limit, 100)))
        .all()
    )
    ids = [o.id for o in orders]
    ratings = {r.order_id: r.score for r in db.query(OrderRating).filter(OrderRating.order_id.in_(ids)).all()} if ids else {}
    receipts: dict[str, Invoice] = {}
    if ids:
        for inv in db.query(Invoice).filter(Invoice.order_id.in_(ids)).order_by(Invoice.created_at.asc()).all():
            receipts[inv.order_id] = inv
    from porterchain_api.merchant_engine.cancel_policy import cancel_allowed

    out = []
    for o in orders:
        inv = receipts.get(o.id)
        retail = not o.merchant_id
        out.append(
            {
                "tracking_number": o.tracking_number,
                "order_number": o.order_number,
                "state": o.state,
                "active": o.state in ACTIVE_STATES,
                "amount_cents": o.amount_cents,
                "currency": (o.currency or "cad").upper(),
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "pickup": (o.pickup or {}).get("formatted") if isinstance(o.pickup, dict) else None,
                "dropoff": (o.dropoff or {}).get("formatted") if isinstance(o.dropoff, dict) else None,
                "extra_drops": len(_stops(o)),
                "rating": ratings.get(o.id),
                "receipt_url": inv.stripe_receipt_url if inv else None,
                "receipt_number": inv.receipt_number if inv else None,
                "can_cancel": retail and o.state != "CANCELLED" and cancel_allowed(o.state),
                "track_url": service.manage_track_url(settings, o),
                "send_again_url": service.send_again_url(settings, o) if retail else None,
            }
        )
    active = [x for x in out if x["active"]]
    spent = sum(x["amount_cents"] or 0 for x in out if x["state"] != "CANCELLED")
    return {
        "summary": {"orders": len(out), "active": len(active), "spent_cents": spent},
        "orders": out,
    }


def report_problem(
    db: Session,
    *,
    customer_id: str,
    order: Order,
    kind: str,
    details: str | None,
) -> dict[str, Any]:
    """Report a problem or request a return → one support ticket (idempotent per order+kind)."""
    from porterchain_api.booking_engine import CustomerService

    if kind not in PROBLEM_KINDS:
        raise ValueError("problem_invalid")
    text = (details or "").strip()[:2000]
    if kind == "other" and len(text) < 3:
        raise ValueError("problem_invalid")
    subject = f"{PROBLEM_KINDS[kind]} · {order.tracking_number}"
    ticket = CustomerService().create_support_ticket(
        db,
        customer_id=customer_id,
        subject=subject[:255],
        description=text or PROBLEM_KINDS[kind],
        order_id=order.id,
        idempotency_key=f"problem:{order.id}:{kind}",
    )
    meta = dict(order.compliance_metadata or {}) if isinstance(order.compliance_metadata, dict) else {}
    reports = list(meta.get("customer_reports") or [])
    if kind not in [r.get("kind") for r in reports]:
        reports.append({"kind": kind, "at": _now().isoformat(), "ticket_id": getattr(ticket, "id", None)})
    meta["customer_reports"] = reports
    if kind == "return":
        meta["return_requested"] = True
    order.compliance_metadata = meta
    db.commit()
    return {"status": "received", "kind": kind, "ticket_id": getattr(ticket, "id", None), "reply_within_hours": 4}


def report_problem_signed(db: Session, settings: Settings, tracking_number: str, token: str, kind: str, details: str | None) -> dict[str, Any]:
    order = service._order_for_manage(db, settings, tracking_number, token)
    if order.merchant_id or not order.customer_id:
        raise ValueError("order_not_found")
    return report_problem(db, customer_id=order.customer_id, order=order, kind=kind, details=details)


def report_problem_owner(db: Session, customer: Customer, tracking_number: str, kind: str, details: str | None) -> dict[str, Any]:
    order = db.query(Order).filter(Order.tracking_number == tracking_number, Order.customer_id == customer.id).first()
    if order is None:
        raise ValueError("order_not_found")
    return report_problem(db, customer_id=customer.id, order=order, kind=kind, details=details)


def ensure_customer(db: Any, claims: Any, settings: Any) -> Any:
    """Resolve (and first-time provision) the signed-in customer; the UoW commits here, not in the router."""
    from porterchain_api.auth.customer import require_customer

    customer = require_customer(db, claims, settings)
    db.commit()
    return customer
