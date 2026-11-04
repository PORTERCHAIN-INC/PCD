"""L97b: an order with an open courier-partner leg is out of our own dispatch."""

from __future__ import annotations

import uuid

import pytest

from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import LogisticsPartnersService
from porterchain_api.admin_engine.operations_service import AdminOperationsService
from porterchain_api.config import get_settings
from porterchain_api.dispatch_engine.partner_hold import held_order_ids
from tests.test_fleet_contracts import _ctx
from tests.test_partner_leg_assign_l97 import _order, _partner

S = LogisticsPartnersService()
OPS = AdminOperationsService()


def _driver(db):
    from porterchain_api.admin_models import Driver

    d = Driver(full_name="L97b D", email=f"l97b_{uuid.uuid4().hex[:6]}@t.test")
    db.add(d)
    db.flush()
    return d


def test_held_orders_skip_queue_and_plan(db) -> None:
    p, ctx = _partner(db), _ctx(db)
    held, free = _order(db), _order(db)
    S.assign_partner_leg(db, ctx, held.id, p.id)
    assert held_order_ids(db, [held.id, free.id]) == {held.id}
    queue = {o.id for o in OPS.dispatch_queue(db, limit=10_000)}
    assert held.id not in queue and free.id in queue
    plan_pool = {o.id for o in FleetPlanService()._orders(db, None)}
    assert held.id not in plan_pool
    assert {o.id for o in FleetPlanService()._orders(db, [held.id, free.id])} == {free.id}


def test_manual_assign_refused_with_partner_name(db) -> None:
    p, o, ctx, d = _partner(db), _order(db), _ctx(db), _driver(db)
    S.assign_partner_leg(db, ctx, o.id, p.id)
    with pytest.raises(ValueError, match=f"order_with_courier_partner: this order is with {p.name}"):
        OPS.assign_driver(db, get_settings(), ctx, o.id, d.id)
    with pytest.raises(ValueError, match="order_with_courier_partner"):
        OPS._assign_driver_no_commit(db, ctx, o.id, d.id)


def test_cancelled_partner_leg_releases_order(db) -> None:
    p, o, ctx = _partner(db), _order(db), _ctx(db)
    leg = S.assign_partner_leg(db, ctx, o.id, p.id)
    S.set_leg_status(db, ctx, leg["id"], "cancelled")
    assert held_order_ids(db, [o.id]) == set()
    assert o.id in {x.id for x in OPS.dispatch_queue(db, limit=10_000)}
