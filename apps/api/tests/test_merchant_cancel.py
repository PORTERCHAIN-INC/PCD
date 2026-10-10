"""AG — cancel cutoff in English; bulk failures are visible."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.booking_engine.numbers import (
    generate_order_number,
    generate_tracking_number,
)
from porterchain_api.booking_models import Order
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderState
from porterchain_api.main import app
from porterchain_api.merchant_engine.cancel_policy import (
    CANCEL_UNTIL_HINT,
    cancel_allowed,
    cancel_error_message,
    cancel_rule,
)
from porterchain_api.merchant_engine.orders_service import MerchantOrdersService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_cancel_words() -> None:
    assert cancel_allowed("DISPATCH_READY") is True
    assert cancel_allowed("DRIVER_ACCEPTED") is True
    assert cancel_allowed("FAILED") is True
    assert cancel_allowed("IN_TRANSIT") is False
    assert cancel_allowed("DRIVER_EN_ROUTE") is False
    assert cancel_rule("BOOKED") == CANCEL_UNTIL_HINT
    assert "on the way to pickup" in cancel_error_message("cannot_cancel:DRIVER_EN_ROUTE")
    assert "in transit" in cancel_error_message("cannot_cancel:IN_TRANSIT").lower()
    assert "already cancelled" in cancel_error_message("already_cancelled").lower()
    assert "IN_TRANSIT" not in cancel_error_message("Invalid order transition IN_TRANSIT -> CANCELLED")
    assert "->" not in cancel_error_message("Invalid order transition IN_TRANSIT -> CANCELLED")


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Cancel Co {suffix}",
        email=f"cancel-{suffix}@test.local",
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


def _order(db, merchant_id: str, state: str) -> Order:
    order = Order(
        order_number=generate_order_number(),
        tracking_number=generate_tracking_number(),
        state=state,
        merchant_id=merchant_id,
        amount_cents=1800,
        currency="cad",
        pickup={"formatted": "1 King St W"},
        dropoff={"formatted": "200 Bay St"},
        scheduled_at=datetime.now(UTC),
    )
    db.add(order)
    db.flush()
    return order


def test_bulk_mixed_cancel_english(db, settings) -> None:
    ctx = _merchant_ctx(db)
    open_order = _order(db, ctx.merchant.id, OrderState.DISPATCH_READY.value)
    moving = _order(db, ctx.merchant.id, OrderState.IN_TRANSIT.value)
    db.commit()

    results = MerchantOrdersService().bulk_action(
        db, settings, ctx, [open_order.id, moving.id], "cancel"
    )
    by_id = {row["order_id"]: row for row in results}
    assert by_id[open_order.id]["ok"] is True
    assert by_id[open_order.id]["status"] == "cancelled"
    assert by_id[moving.id]["ok"] is False
    assert "in transit" in str(by_id[moving.id]["message"]).lower()
    assert "IN_TRANSIT" not in str(by_id[moving.id]["message"])
    assert moving.tracking_number == by_id[moving.id]["tracking_number"]


def test_cancel_http_english(db, settings, monkeypatch) -> None:
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.orders_tracking.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx = _merchant_ctx(db)
        ready = _order(db, ctx.merchant.id, OrderState.DISPATCH_READY.value)
        moving = _order(db, ctx.merchant.id, OrderState.IN_TRANSIT.value)
        db.commit()
        holder["ctx"] = ctx

        blocked = client.post(f"/v1/merchant/orders/{moving.id}/cancel")
        assert blocked.status_code == 400
        assert "in transit" in blocked.json()["detail"].lower()
        assert "->" not in blocked.json()["detail"]

        ok = client.post(f"/v1/merchant/orders/{ready.id}/cancel")
        assert ok.status_code == 200
        assert ok.json()["state"] == "CANCELLED"

        bulk = client.post(
            "/v1/merchant/orders/bulk",
            json={"order_ids": [moving.id], "action": "cancel"},
        )
        assert bulk.status_code == 200
        body = bulk.json()
        assert body["failed_count"] == 1
        assert body["ok_count"] == 0
        assert "in transit" in body["results"][0]["message"].lower()
    finally:
        app.dependency_overrides.clear()
