"""Delivery options on the remaining merchant paths: multi-stop route import, CSV, merchant
default (applied to every booking incl. Shopify), per-order edit (Shopify orders page)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

import porterchain_api.main  # noqa: F401
from porterchain_api.booking_models import Order, OrderEvent
from porterchain_api.domain.delivery_options import from_row, label_line, with_default
from porterchain_api.merchant_engine import delivery_options_service as svc
from porterchain_api.merchant_engine.import_confirm import _address_input, driver_notes
from porterchain_api.merchant_engine.import_rows import rows_to_stops
from porterchain_api.merchant_engine.stop_cargo import cargo_stop
from porterchain_api.schemas_merchant import RouteImportStopInput


def _order(db, ctx, *, state="DISPATCH_READY", source="SHOPIFY", merchant_id=None) -> Order:
    o = Order(order_number=f"ORD-T-{uuid4().hex[:8]}", tracking_number=f"PC-T-{uuid4().hex[:8]}", state=state,
              merchant_id=merchant_id or ctx.merchant.id, amount_cents=1000, currency="cad",
              order_source=source, scheduled_at=datetime.now(UTC),
              pickup={"formatted": "1 King St W", "lat": 43.65, "lng": -79.38},
              dropoff={"formatted": "200 Bay St", "lat": 43.645, "lng": -79.38},
              compliance_metadata={"shopify": {"order_name": "#1042"}})
    db.add(o)
    db.commit()
    return o


def test_csv_columns_become_options() -> None:
    assert from_row({"drop_method": "Leave at door", "buzzer": "12#", "call_on_arrival": "yes",
                     "load_help": "1", "unit": "4"}) == {
        "drop_method": "leave_at_door", "buzzer": "12#", "call_on_arrival": True, "load_help": True, "unit": "4"}
    assert from_row({"delivery_option": "concierge"}) == {"drop_method": "concierge"}
    assert from_row({"drop_method": "hand delivery"}) == {"drop_method": "hand_to_recipient"}
    assert from_row({"notes": "x"}) is None


def test_route_csv_and_multi_stop_carry_options_to_the_order_and_driver() -> None:
    stops = rows_to_stops([
        {"stop_type": "pickup", "address": "1 King St W, Toronto"},
        {"stop_type": "drop", "address": "200 Bay St, Toronto", "buzzer": "77", "drop_method": "door"},
        {"stop_type": "drop", "address": "10 Dundas St E, Toronto", "notes": "side door"},
    ])
    drops = [s for s in stops if s["stop_type"] == "drop"]
    assert drops[0]["delivery_options"] == {"drop_method": "leave_at_door", "buzzer": "77"}
    assert drops[1]["delivery_options"] is None
    # Portal multi-stop planner sends options per stop.
    body = RouteImportStopInput(address="200 Bay St", delivery_options={"drop_method": "concierge", "unit": "9"})
    stop = {**body.model_dump(), "sequence": 2, "formatted": "200 Bay St"}
    assert cargo_stop(stop)["delivery_options"] == {"drop_method": "concierge", "unit": "9"}
    addr = _address_input(stop).model_dump()
    assert addr["delivery_options"]["drop_method"] == "concierge"
    notes = driver_notes([stop])
    assert "Leave with concierge / reception" in notes and "Unit 9" in notes


def test_bulk_csv_row_dropoff_gets_options(monkeypatch) -> None:
    from porterchain_api.merchant_engine.bulk_service import MerchantBulkService

    svc_ = MerchantBulkService.__new__(MerchantBulkService)
    row = {"dropoff": "200 Bay St", "dropoff_lat": "43.645", "dropoff_lng": "-79.38", "buzzer": "55",
           "call_on_arrival": "true"}
    addr = svc_._address_from_row(row, prefix="dropoff")  # noqa: SLF001
    assert addr.model_dump()["delivery_options"] == {"buzzer": "55", "call_on_arrival": True}
    pick = svc_._address_from_row({"pickup": "1 King", "pickup_lat": "43.6", "pickup_lng": "-79.3", "buzzer": "1"},
                                  prefix="pickup")  # noqa: SLF001
    assert "delivery_options" not in pick.model_dump()


def test_merchant_default_fills_only_empty_bookings(db, merchant_ctx) -> None:
    assert svc.set_default(db, merchant_ctx, {"drop_method": "leave_at_door", "junk": 1}) == {
        "drop_method": "leave_at_door"}
    m = merchant_ctx.merchant
    assert with_default({"formatted": "x"}, m)["delivery_options"] == {"drop_method": "leave_at_door"}
    chosen = {"formatted": "x", "delivery_options": {"drop_method": "concierge"}}
    assert with_default(chosen, m) == chosen
    assert label_line(with_default({"formatted": "x"}, m)) == "Leave at door"
    assert svc.set_default(db, merchant_ctx, {}) == {} and svc.get_default(merchant_ctx) == {}


def test_create_shipment_applies_default(db, merchant_ctx, settings, monkeypatch) -> None:
    from porterchain_api.merchant_engine import booking_service as bs

    svc.set_default(db, merchant_ctx, {"drop_method": "leave_at_door", "call_on_arrival": True})
    captured = {}
    real = bs.with_default_delivery_options

    def spy(dropoff, merchant):
        captured["out"] = real(dropoff, merchant)
        return captured["out"]

    monkeypatch.setattr(bs, "with_default_delivery_options", spy)
    import inspect

    assert "with_default_delivery_options(" in inspect.getsource(bs.MerchantBookingService.create_shipment)
    assert spy({"formatted": "x"}, merchant_ctx.merchant)["delivery_options"] == {
        "drop_method": "leave_at_door", "call_on_arrival": True}


def test_per_order_edit_from_shopify_orders_page(db, merchant_ctx) -> None:
    o = _order(db, merchant_ctx)
    listed = svc.shopify_orders(db, merchant_ctx)
    row = next(r for r in listed if r["order_id"] == o.id)
    assert row["shopify_order_name"] == "#1042" and row["editable"] and row["delivery_options"] == {}
    out = svc.update_order(db, merchant_ctx, o.id, {"drop_method": "hand_to_recipient", "buzzer": "3"})
    assert out["delivery_options"] == {"drop_method": "hand_to_recipient", "buzzer": "3"}
    assert db.get(Order, o.id).dropoff["delivery_options"]["buzzer"] == "3"
    assert db.query(OrderEvent).filter_by(order_id=o.id, event_type="order.delivery_options_updated").count() == 1
    done = _order(db, merchant_ctx, state="DELIVERED")
    with pytest.raises(svc.DeliveryOptionsError, match="order_not_editable"):
        svc.update_order(db, merchant_ctx, done.id, {"drop_method": "concierge"})


def test_cannot_edit_another_merchants_order(db, merchant_ctx) -> None:
    from porterchain_api.merchant_models import Merchant

    other = Merchant(company_name="Other", email=f"o-{uuid4().hex[:6]}@t.test", status="ACTIVE")
    db.add(other)
    db.commit()
    o = _order(db, merchant_ctx, merchant_id=other.id)
    with pytest.raises(svc.DeliveryOptionsError, match="order_not_found"):
        svc.update_order(db, merchant_ctx, o.id, {"drop_method": "concierge"})
    assert all(r["order_id"] != o.id for r in svc.shopify_orders(db, merchant_ctx))


def test_routes_registered() -> None:
    from porterchain_api.routers.merchant import router

    paths = {(r.path, m) for r in router.routes for m in getattr(r, "methods", ())}
    assert ("/v1/merchant/settings/delivery-defaults", "PUT") in paths
    assert ("/v1/merchant/orders/{order_id}/delivery-options", "PATCH") in paths
    assert ("/v1/merchant/shopify/orders", "GET") in paths
