"""Collect-only jobs: pickup -> OUR warehouse, parcel waits there, delivery leg released later."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.fleet_plan_service import FleetPlanService
from porterchain_api.admin_engine.logistics_partners_service import HubSplitService
from porterchain_api.booking_models import Order
from porterchain_api.config import get_settings
from porterchain_api.services import collect_only as co
from porterchain_api.dispatch_engine.hub_legs import AT_HUB, TO_HUB, hub_leg
from porterchain_driver.next_stop import NextStopResolver
from porterchain_driver.stops import StopsService
from tests.test_dispatch_phase2 import S, W, _ctx, _driver, _order
from tests.test_hub_split import HUB, _events, _hub, _quiet  # noqa: F401  (autouse fixture)

pytestmark = pytest.mark.usefixtures("quiet_pool")


def _collect_order(db: Session, hub, **kw) -> Order:
    o = _order(db, W, S, **kw)
    o.compliance_metadata = co.mark({}, hub)
    co.attach_legs(db, o, hub, actor_type="admin", actor_id=None)
    db.commit()
    return o


def test_end_to_end_pickup_to_warehouse_then_release(db: Session) -> None:
    ctx, hub, first = _ctx(db), _hub(db), _driver(db)
    o = _collect_order(db, hub, state="PICKED_UP", assigned_driver_id=first.id)
    assert hub_leg(db, o.id).stage == TO_HUB and co.is_collect_only(o)

    # Driver: the drop is our warehouse — no receiver code, no photo, no out-for-delivery.
    nxt = NextStopResolver().resolve(db, first)
    assert nxt["hub_leg"] == "to_hub" and nxt["address"]["lat"] == HUB["lat"]
    svc = StopsService()
    svc.start_delivery(db, first, f"{o.id}-dropoff")
    arrived = svc.arrive_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    assert not arrived.otp_required
    svc.deliver_stop(db, first, f"{o.id}-dropoff")
    db.commit()
    order = db.get(Order, o.id)
    assert order.state == "PICKED_UP" and order.assigned_driver_id is None
    assert _events(db, o.id, "order.in_transit") == 0 and _events(db, o.id, "order.hub_received") == 1
    assert hub_leg(db, o.id).stage == AT_HUB

    # Admin sees "At warehouse – awaiting delivery"; Plan the day leaves it alone until released.
    view = HubSplitService().view(db, o.id)
    assert view["collect_only"] and view["delivery_held"] and view["awaiting_delivery"]
    assert view["status_label"] == co.AWAITING_LABEL
    plan = FleetPlanService()
    assert o.id not in {x.id for x in plan._orders(db, None)}  # noqa: SLF001

    HubSplitService().release_delivery_leg(db, get_settings(), ctx, o.id)
    assert not co.is_held(db, o.id)
    assert o.id in {x.id for x in plan._orders(db, None)}  # noqa: SLF001
    assert plan._hub_override(db, db.get(Order, o.id)).pickup["lat"] == HUB["lat"]  # noqa: SLF001

    van = _driver(db)
    HubSplitService().release_delivery_leg(db, get_settings(), ctx, o.id, driver_id=van.id)
    order = db.get(Order, o.id)
    assert order.assigned_driver_id == van.id and order.state == "PICKED_UP"
    assert _events(db, o.id, "order.delivery_leg_released") == 2


def test_release_before_pickup_books_delivery_driver_for_after_drop(db: Session) -> None:
    ctx, hub = _ctx(db), _hub(db)
    o = _collect_order(db, hub)
    van = _driver(db)
    HubSplitService().release_delivery_leg(db, get_settings(), ctx, o.id, driver_id=van.id)
    assert hub_leg(db, o.id).delivery_driver_id == van.id
    assert db.get(Order, o.id).assigned_driver_id is None  # pickup driver still to plan


def test_hub_drop_gps_check(db: Session, monkeypatch) -> None:
    import porterchain_driver.navigation as nav

    hub, first = _hub(db), _driver(db)
    o = _collect_order(db, hub, state="PICKED_UP", assigned_driver_id=first.id)
    monkeypatch.setattr(nav, "ENFORCE_STOP_PRESENCE", True)
    far = SimpleNamespace(lat=W["lat"], lng=W["lng"])
    monkeypatch.setattr("porterchain_api.driver_engine.last_known.read_last_known", lambda _d: far)
    with pytest.raises(ValueError, match="not_at_stop"):
        StopsService().deliver_stop(db, first, f"{o.id}-dropoff")


def test_guards(db: Session) -> None:
    ctx = _ctx(db)
    plain = _order(db, W, S)
    db.commit()
    with pytest.raises(ValueError, match="not_a_warehouse_order"):
        HubSplitService().release_delivery_leg(db, get_settings(), ctx, plain.id)
    with pytest.raises(LookupError):
        HubSplitService().release_delivery_leg(db, get_settings(), ctx, "nope")
    assert co.for_booking(db, SimpleNamespace(service_mode="standard")) is None
    with pytest.raises(ValueError, match="collect_only_single_pickup"):
        co.for_booking(db, SimpleNamespace(service_mode="collect_only", additional_stops=[{"x": 1}]))


def test_no_warehouse_is_a_clear_error(db: Session) -> None:
    with pytest.raises(ValueError, match="no_warehouse_for_collect_only"):
        co.warehouse(db, "missing-id")


def test_admin_builder_prices_pickup_to_warehouse(db: Session, settings) -> None:
    from porterchain_api.admin_engine.order_builder_service import OrderBuilderService
    from porterchain_api.schemas_admin import AdminCreateOrderRequest, AdminOrderStopInput
    from tests.test_pricing_audit_gates import _merchant_ctx

    mctx, hub = _merchant_ctx(db), _hub(db)
    db.commit()
    seen = {}

    def calc(req):
        seen["req"] = req
        return SimpleNamespace(final_cents=2500, metadata={})

    body = AdminCreateOrderRequest(
        merchant_id=mctx.merchant.id,
        order_kind="collect_only",
        stops=[
            AdminOrderStopInput(type="pickup", sequence=0, formatted=W["formatted"], lat=W["lat"], lng=W["lng"]),
            AdminOrderStopInput(type="dropoff", sequence=1, formatted=S["formatted"], lat=S["lat"], lng=S["lng"]),
        ],
        scheduled_at=datetime.now(UTC),
    )
    with (
        patch("porterchain_api.admin_engine.order_builder_service.resolve_route_distance",
              return_value=(8_000, 900, "haversine")),
        patch("porterchain_api.admin_engine.order_builder_service.get_pricing_service",
              return_value=SimpleNamespace(calculate_merchant=calc)),
        patch.object(co, "warehouse", lambda _db, _id=None: hub),
    ):
        out = OrderBuilderService().create(db, settings, _ctx(db), body)
    req = seen["req"]
    assert req.dropoff.lat == HUB["lat"] and req.merchant_id == mctx.merchant.id
    order = db.get(Order, out["order_id"])
    assert order.amount_cents == 2500 and co.is_collect_only(order)
    assert order.dropoff["lat"] == S["lat"]  # the receiver stays on file for the later delivery
    assert co.is_held(db, order.id) and hub_leg(db, order.id).stage == TO_HUB


def test_merchant_booking_collect_only_prices_to_warehouse(db: Session, settings) -> None:
    from porterchain_api.merchant_engine.booking_service import MerchantBookingService
    from tests.test_merchant_wave2_floor import _body
    from tests.test_merchant_wave2_floor import _ctx as _mctx

    ctx, hub = _mctx(db), _hub(db)
    db.commit()
    svc = MerchantBookingService()
    std = svc.build_pricing_request(ctx, _body())
    with (
        patch("porterchain_api.merchant_engine.booking_service.transition_to_dispatch_ready",
              side_effect=lambda db, order, **_k: order),
        patch.object(co, "warehouse", lambda _db, _id=None: hub),
    ):
        order = svc.create_shipment(db, settings, ctx, _body(service_mode="collect_only"))
    assert co.is_collect_only(order) and co.is_held(db, order.id)
    assert order.compliance_metadata["collect_only"]["priced_to"] == "warehouse"
    with patch.object(co, "warehouse", lambda _db, _id=None: hub):
        req = svc.build_pricing_request(ctx, _body(service_mode="collect_only"), db=db)
    assert req.dropoff.lat == HUB["lat"] and std.dropoff.lat != HUB["lat"]
    assert hub_leg(db, order.id).stage == TO_HUB
