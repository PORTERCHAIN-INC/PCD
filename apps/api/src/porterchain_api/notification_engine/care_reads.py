"""Open claim and ticket counts for the notification care panel. Reads only.

Lives here so notification_engine does not import support_engine.
"""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, SupportTicket
from porterchain_api.booking_models import Order

_OPEN_TICKET = ("open", "in_progress", "waiting")
_OPEN_CLAIM = ("open", "investigating", "pending")


def open_ticket_count(
    db: Session, *, merchant_id: str | None = None, customer_id: str | None = None
) -> int:
    q = db.query(func.count(SupportTicket.id)).filter(SupportTicket.status.in_(_OPEN_TICKET))
    if merchant_id is not None:
        q = q.filter(SupportTicket.merchant_id == merchant_id)
    elif customer_id is not None:
        q = q.filter(SupportTicket.customer_id == customer_id)
    else:
        return 0
    return int(q.scalar() or 0)


def open_claim_count_for_driver(db: Session, driver_id: str) -> int:
    return int(
        db.query(func.count(Claim.id))
        .join(Order, Order.id == Claim.order_id)
        .filter(
            Order.assigned_driver_id == driver_id,
            Claim.status.in_(_OPEN_CLAIM),
        )
        .scalar()
        or 0
    )
