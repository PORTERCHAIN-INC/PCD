"""L140: final/only partner leg delivered -> order DELIVERED (+ order.delivered event); middle leg does not."""

from __future__ import annotations

from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.dispatch_engine.models import OrderLeg
from porterchain_api.domain.states import OrderState
from tests.test_fleet_contracts import _ctx
from tests.test_partner_leg_assign_l97 import S, _order, _partner


def _walk(db, ctx, leg_id):
    for st in ("requested", "accepted", "picked_up", "delivered"):
        S.set_leg_status(db, ctx, leg_id, st)


def test_only_leg_delivered_moves_order_to_delivered(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    _walk(db, ctx, leg["id"])
    db.expire_all()
    assert db.get(Order, o.id).state == OrderState.DELIVERED.value
    ev = db.query(OrderEvent).filter(OrderEvent.order_id == o.id, OrderEvent.event_type == "order.delivered").all()
    assert len(ev) == 1 and ev[0].payload.get("source") == "partner_leg"


def test_middle_leg_only_completes_that_leg(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    db.add(OrderLeg(order_id=o.id, seq=(db.get(OrderLeg, leg["id"]).seq or 0) + 1, mode="local", status="planned"))
    db.flush()
    _walk(db, ctx, leg["id"])
    db.expire_all()
    assert db.get(OrderLeg, leg["id"]).status == "delivered"
    assert db.get(Order, o.id).state == OrderState.DISPATCH_READY.value


def test_backfill_syncs_order_for_leg_delivered_before_fix(db) -> None:
    """Leg delivered pre-fix (order left DISPATCH_READY) -> admin 'Mark order delivered' syncs it."""
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    row = db.get(OrderLeg, leg["id"])
    row.status = "delivered"  # simulate the pre-fix state
    db.flush()
    item = next(x for x in S.partner_legs(db) if x["id"] == leg["id"])
    assert item["order_needs_sync"] is True
    out = S.sync_order_from_leg(db, ctx, leg["id"])
    db.expire_all()
    assert db.get(Order, o.id).state == OrderState.DELIVERED.value
    assert out["order_needs_sync"] is False
