"""How many stops are ahead of this order on the driver's current run.

Source of truth (first match wins), per in-flight order on the same driver:
1. ``compliance_metadata.route_sequence`` (set by the route optimiser / import), or
2. ``DriverStopMeta.meta["sequence"]`` (driver app stop order).
If this order has no sequence we only answer when it is the driver's last
in-flight stop (0 ahead); otherwise ``None`` (unknown, UI hides the count).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.booking_models import Order
from porterchain_api.customer_experience.context import EN_ROUTE_STATES, meta_of


def _sequence(order: Order, stop_meta: dict[str, dict[str, Any]]) -> int | None:
    raw = meta_of(order).get("route_sequence")
    if raw is None:
        raw = (stop_meta.get(order.id) or {}).get("sequence")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def driver_run(db: Session, driver_id: str) -> list[Order]:
    return (
        db.query(Order)
        .filter(Order.assigned_driver_id == driver_id, Order.state.in_(sorted(EN_ROUTE_STATES)))
        .order_by(Order.created_at.asc())
        .limit(200)
        .all()
    )


def stops_ahead(db: Session, order: Order, *, run: list[Order] | None = None) -> int | None:
    if order.state == "AT_DESTINATION":
        return 0
    if order.state not in EN_ROUTE_STATES or not order.assigned_driver_id:
        return None
    from porterchain_api.driver_models import DriverStopMeta

    run = run if run is not None else driver_run(db, order.assigned_driver_id)
    ids = [o.id for o in run] or [order.id]
    stop_meta = {
        row.order_id: (row.meta if isinstance(row.meta, dict) else {})
        for row in db.query(DriverStopMeta).filter(DriverStopMeta.order_id.in_(ids)).all()
    }
    others = [o for o in run if o.id != order.id]
    mine = _sequence(order, stop_meta)
    if mine is None:
        return 0 if not others else None
    ahead = 0
    for other in others:
        seq = _sequence(other, stop_meta)
        if other.state == "AT_DESTINATION" or (seq is not None and seq < mine):
            ahead += 1
    return ahead
