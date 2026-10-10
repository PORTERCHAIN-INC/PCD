"""Right to erasure (GDPR Art. 17 / PIPEDA principle 4.5) with legal retention respected.

Personal contact data is removed from customer accounts and from order pickup/drop
contacts. What the law makes us keep stays: invoices, payments and the ledger (CA 6 y,
AT 7 y), plus each order's city/FSA and amounts so the books still reconcile. A dry run
shows exactly what would change. Nothing is sent.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Customer, Order
from porterchain_api.platform.privacy_access import _digits, subject_access_export


def _fsa(addr: dict[str, Any]) -> str | None:
    p = str(addr.get("postal") or addr.get("postal_code") or "").replace(" ", "").upper()
    return p[:3] or None


def _scrub(addr: Any) -> dict[str, Any]:
    if not isinstance(addr, dict):
        return {"erased": True}
    out: dict[str, Any] = {k: addr[k] for k in ("city", "province", "country") if addr.get(k)}
    if _fsa(addr):
        out["postal_fsa"] = _fsa(addr)
    if addr.get("lat") is not None and addr.get("lng") is not None:  # ~1 km, keeps analytics, not a home
        out["lat_round"], out["lng_round"] = round(float(addr["lat"]), 2), round(float(addr["lng"]), 2)
    out["formatted"] = ", ".join(str(out[k]) for k in ("city", "province") if out.get(k)) or "Erased"
    out["erased"] = True
    return out


def erase_subject(
    db: Session, *, email: str | None = None, phone: str | None = None, dry_run: bool = True, actor: str = "admin"
) -> dict[str, Any]:
    found = subject_access_export(db, email=email, phone=phone)
    email_l = (email or "").strip().lower()
    digits = _digits(phone)
    numbers = {o["order_number"]: o["role"] for o in found["orders"]}
    orders = db.query(Order).filter(Order.order_number.in_(list(numbers))).all() if numbers else []
    customers = db.query(Customer).filter(Customer.id.in_([c["id"] for c in found["customers"]])).all() if found["customers"] else []
    now = datetime.now(UTC).isoformat()
    plan = {
        "customers": len(customers),
        "orders_scrubbed": len(orders),
        "kept_for_law": "Invoices, payments, ledger, order amounts/city/FSA (tax retention)",
        "dry_run": dry_run,
    }
    if dry_run:
        return plan

    def mentions(addr: Any) -> bool:
        blob = str(addr or "").lower()
        return bool((email_l and email_l in blob) or (digits and digits in "".join(ch for ch in blob if ch.isdigit())))

    cids = {c.id for c in customers}
    for o in orders:
        whole = o.customer_id in cids
        if whole or mentions(o.pickup):
            o.pickup = _scrub(o.pickup)
        if whole or mentions(o.dropoff):
            o.dropoff = _scrub(o.dropoff)
        if whole:
            o.special_instructions = None
        meta = dict(o.compliance_metadata or {})
        meta["erasure"] = {"at": now, "by": actor}
        o.compliance_metadata = meta
    for c in customers:
        c.email = f"erased-{c.id[:8]}@erased.invalid"
        c.phone = None
        c.full_name = None
    db.flush()
    return {**plan, "erased_at": now}
