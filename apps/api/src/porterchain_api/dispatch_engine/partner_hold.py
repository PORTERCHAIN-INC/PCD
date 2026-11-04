"""Orders handed to a courier (contractor fleet) partner stay out of our own dispatch.

Ravi (L97 follow-up): an order with an open courier leg must not reach Plan the day,
the dispatch queue, or a manual / bulk driver assign. Cancel the partner job to release it.
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy.orm import Session

HOLD_ERROR = "order_with_courier_partner"


def _open_courier(db: Session):
    from porterchain_api.dispatch_engine.models import OrderLeg

    return db.query(OrderLeg).filter(OrderLeg.mode == "courier", OrderLeg.status != "cancelled")


def held_order_ids(db: Session, order_ids: Iterable[str] | None = None) -> set[str]:
    from porterchain_api.dispatch_engine.models import OrderLeg

    q = _open_courier(db)
    if order_ids is not None:
        ids = list(order_ids)
        if not ids:
            return set()
        q = q.filter(OrderLeg.order_id.in_(ids))
    return {leg.order_id for leg in q.all() if isinstance(leg, OrderLeg)}


def assert_not_with_partner(db: Session, order_id: str) -> None:
    """Raise ValueError when an open courier leg owns this order."""
    from porterchain_api.dispatch_engine.models import LogisticsPartner, OrderLeg

    leg = _open_courier(db).filter(OrderLeg.order_id == order_id).first()
    if not isinstance(leg, OrderLeg):  # none open (or a stub session in unit tests)
        return
    p = db.get(LogisticsPartner, leg.partner_id) if leg.partner_id else None
    name = getattr(p, "name", None) or "a fleet partner"
    raise ValueError(f"{HOLD_ERROR}: this order is with {name}. Cancel the partner job first to give it to our drivers.")
