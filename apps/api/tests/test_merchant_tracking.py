"""Merchant Track page and Order 360 share one company-scoped snapshot."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import generate_order_number, generate_tracking_number
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.tracking_service import (
    MerchantTrackingService,
    public_track_url,
    tracking_error_message,
)
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.booking_models import Order


def _addr() -> dict:
    return {"formatted": "1 King St W, Toronto", "lat": 43.6488, "lng": -79.3817}


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Track Co {suffix}",
        email=f"track-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def _order(db, merchant_id: str) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=OrderState.IN_TRANSIT.value,
        merchant_id=merchant_id,
        amount_cents=2500,
        currency="cad",
        pickup=_addr(),
        dropoff=_addr(),
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_tracking_error_message_english():
    assert tracking_error_message("order_not_found") == "That order was not found."
    assert "tracking number" in tracking_error_message("tracking_not_found").lower()


def test_track_by_number_and_order_number(db, settings):
    ctx = _merchant_ctx(db)
    other = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id)
    foreign = _order(db, other.merchant.id)
    db.commit()

    svc = MerchantTrackingService()
    by_track = svc.track_by_number(db, settings, ctx, order.tracking_number)
    by_order = svc.track_by_number(db, settings, ctx, order.order_number.lower())
    live = svc.live_tracking(db, settings, ctx, order.id)

    assert by_track["order_id"] == order.id
    assert by_order["order_id"] == order.id
    assert live["order_id"] == order.id
    assert by_track["public_track_url"] == public_track_url(settings, order.tracking_number)
    assert live["public_track_url"] == by_track["public_track_url"]
    assert by_track["order_number"] == order.order_number
    assert by_track["branding"]["company_name"] == ctx.merchant.company_name
    assert live["branding"]["company_name"] == ctx.merchant.company_name
    assert live["display_state"] == "In transit"
    blob = str(live)
    assert "fleetbase" not in blob.lower()
    assert "valhalla" not in blob.lower()
    assert "osrm" not in blob.lower()
    if live.get("eta"):
        assert "source" not in live["eta"]
    assert "live" not in live
    assert "fleetbase_order_id" not in live

    dash = svc.dashboard(db, settings, ctx)
    assert dash["orders"]
    assert dash["orders"][0]["display_state"] == "In transit"
    assert "fleetbase" not in str(dash).lower()

    with pytest.raises(LookupError, match="tracking_not_found"):
        svc.track_by_number(db, settings, ctx, foreign.tracking_number)
    with pytest.raises(LookupError, match="order_not_found"):
        svc.live_tracking(db, settings, ctx, foreign.id)


@pytest.fixture
def merchant_client(db, settings, monkeypatch):
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.orders_tracking.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app), holder
    app.dependency_overrides.clear()


def test_track_http_same_snapshot_and_english_404(merchant_client, db, settings):
    client, holder = merchant_client
    ctx = _merchant_ctx(db)
    other = _merchant_ctx(db)
    order = _order(db, ctx.merchant.id)
    foreign = _order(db, other.merchant.id)
    db.commit()
    holder["ctx"] = ctx

    missing = client.get("/v1/merchant/track/DOES-NOT-EXIST")
    assert missing.status_code == 404
    assert "No shipment matches" in missing.json()["detail"]

    by_order = client.get(f"/v1/merchant/track/{order.order_number}")
    assert by_order.status_code == 200
    live = by_order.json()["live_tracking"]
    assert live["order_id"] == order.id
    assert live["display_state"] == "In transit"
    assert "fleetbase" not in str(live).lower()
    assert live["public_track_url"] == public_track_url(settings, order.tracking_number)

    on_order = client.get(f"/v1/merchant/orders/{order.id}/tracking")
    assert on_order.status_code == 200
    assert on_order.json()["order_id"] == order.id
    assert on_order.json()["public_track_url"] == live["public_track_url"]

    stolen = client.get(f"/v1/merchant/orders/{foreign.id}/tracking")
    assert stolen.status_code == 404
    assert "not found" in stolen.json()["detail"].lower()
