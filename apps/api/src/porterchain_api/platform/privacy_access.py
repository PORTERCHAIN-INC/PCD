"""PIPEDA right of access: everything we hold about one person, as one JSON bundle.

Read-only. Matches by email and/or phone across customers, orders (sender and
recipient contacts), and support tickets. Admin reviews the bundle and sends it
to the requester themselves (we never auto-send). PIPEDA: respond within 30 days.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session

from porterchain_api.admin_models import SupportTicket
from porterchain_api.booking_models import Customer, Order

RESPONSE_DAYS = 30


def _digits(phone: str | None) -> str:
    d = re.sub(r"\D", "", phone or "")
    return d[-10:] if len(d) >= 10 else ""


def subject_access_export(db: Session, *, email: str | None = None, phone: str | None = None) -> dict[str, Any]:
    email = (email or "").strip().lower()
    digits = _digits(phone)
    if not email and not digits:
        raise ValueError("email_or_phone_required")
    if email and "@" not in email:
        raise ValueError("invalid_email")

    cust_q = []
    if email:
        cust_q.append(Customer.email.ilike(email))
    if digits:
        cust_q.append(Customer.phone.ilike(f"%{digits[-7:]}%"))
    customers = db.query(Customer).filter(or_(*cust_q)).all()
    if digits:  # tighten the loose phone match to the full 10 digits
        customers = [c for c in customers if (email and (c.email or "").lower() == email) or _digits(c.phone) == digits]
    cids = [c.id for c in customers]

    ord_q = []
    if cids:
        ord_q.append(Order.customer_id.in_(cids))
    for col in (Order.pickup, Order.dropoff):
        if email:
            ord_q.append(cast(col, String).ilike(f"%{email}%"))
        if digits:
            ord_q.append(cast(col, String).ilike(f"%{digits[-4:]}%"))
    orders = db.query(Order).filter(or_(*ord_q)).order_by(Order.created_at.desc()).limit(2000).all()

    def mentions(addr: Any) -> bool:
        blob = str(addr or "").lower()
        return bool((email and email in blob) or (digits and digits in re.sub(r"\D", "", blob)))

    orders = [o for o in orders if o.customer_id in cids or mentions(o.pickup) or mentions(o.dropoff)]
    tickets = db.query(SupportTicket).filter(SupportTicket.customer_id.in_(cids)).all() if cids else []
    now = datetime.now(UTC)
    return {
        "generated_at": now.isoformat(),
        "respond_by": (now + timedelta(days=RESPONSE_DAYS)).date().isoformat(),
        "query": {"email": email or None, "phone_last4": digits[-4:] or None},
        "customers": [
            {"id": c.id, "email": c.email, "phone": c.phone, "full_name": c.full_name} for c in customers
        ],
        "orders": [
            {
                "order_number": o.order_number,
                "created_at": o.created_at.isoformat() if o.created_at else None,
                "state": o.state,
                "role": "customer" if o.customer_id in cids else ("sender" if mentions(o.pickup) else "recipient"),
                "pickup": o.pickup if (o.customer_id in cids or mentions(o.pickup)) else None,
                "dropoff": o.dropoff if (o.customer_id in cids or mentions(o.dropoff)) else None,
                "special_instructions": o.special_instructions,
            }
            for o in orders
        ],
        "support_tickets": [
            {"id": t.id, "subject": t.subject, "status": t.status, "description": t.description} for t in tickets
        ],
        "counts": {"customers": len(customers), "orders": len(orders), "support_tickets": len(tickets)},
        "note": "GPS breadcrumbs and POD photos are kept under Dispatch → retention and are not tied to recipients.",
    }
