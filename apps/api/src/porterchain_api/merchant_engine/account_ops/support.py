"""Support rollup for one merchant: open tickets, claims and delivery exceptions (read-only)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session


def support_rollup(db: Session, merchant_id: str, *, limit: int = 25) -> dict[str, Any]:
    from porterchain_api.admin_models import Claim, SupportTicket
    from porterchain_api.booking_models import Order, OrderException

    tickets = (
        db.query(SupportTicket)
        .filter(SupportTicket.merchant_id == merchant_id)
        .order_by(SupportTicket.created_at.desc())
        .limit(limit)
        .all()
    )
    claims = (
        db.query(Claim).filter(Claim.merchant_id == merchant_id).order_by(Claim.created_at.desc()).limit(limit).all()
    )
    exceptions = (
        db.query(OrderException, Order.tracking_number)
        .join(Order, Order.id == OrderException.order_id)
        .filter(Order.merchant_id == merchant_id)
        .order_by(OrderException.created_at.desc())
        .limit(limit)
        .all()
    )

    def iso(dt):
        return dt.isoformat() if dt else None

    return {
        "tickets": [
            {"id": t.id, "subject": t.subject, "status": t.status, "priority": t.priority,
             "category": t.category, "order_id": t.order_id, "created_at": iso(t.created_at)}
            for t in tickets
        ],
        "claims": [
            {"id": c.id, "type": c.claim_type, "status": c.status, "order_id": c.order_id,
             "created_at": iso(c.created_at), "resolved_at": iso(c.resolved_at)}
            for c in claims
        ],
        "exceptions": [
            {"id": e.id, "type": e.type, "status": e.status, "order_id": e.order_id,
             "tracking_number": tn, "created_at": iso(e.created_at)}
            for e, tn in exceptions
        ],
    }
