"""Shopify control plane: ingress pause, DLQ, hold-at-BOOKED, release, replay."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.shopify_control_service import (
    release_shopify_order_to_fleetbase,
    set_auto_dispatch,
    set_ingress_paused,
)
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.booking_models import Order
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.shopify_ingress_dlq import (
    REASON_INGRESS_PAUSED,
    REASON_MISSING_PICKUP,
    list_ingress_dlq,
)
from porterchain_api.merchant_models import Merchant, ShopifyIngressDlq, ShopifyShop


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        shopify_api_secret="shpss_test",
        fleetbase_dispatch_bridge=False,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def shopify_shop(db: Session) -> ShopifyShop:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"Ctrl Co {suffix}",
        email=f"ctrl-{suffix}@test.invalid",
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    row = ShopifyShop(
        merchant_id=merchant.id,
        shop_domain=f"ctrl-{suffix}.myshopify.com",
        scopes="read_orders,write_fulfillments",
        installed_at=datetime.now(UTC),
        ingress_paused=False,
        auto_dispatch=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _admin_ctx():
    user = MagicMock()
    user.id = "admin-test-1"
    ctx = MagicMock()
    ctx.user = user
    return ctx


def test_ingress_paused_holds_to_dlq(db: Session, shopify_shop: ShopifyShop) -> None:
    shopify_shop.ingress_paused = True
    db.commit()
    settings = _settings()
    body = {"id": 55001, "name": "#55001", "shipping_address": {"address1": "1 Main", "city": "Toronto", "zip": "M5V1A1"}}
    result = shopify.process_queued_webhook(
        db,
        settings,
        {
            "action": "shopify_orders_create",
            "shop_domain": shopify_shop.shop_domain,
            "topic": "orders/create",
            "raw_body": json.dumps(body),
        },
    )
    assert result.get("skipped") == "ingress_paused"
    rows = list_ingress_dlq(db, shopify_shop.merchant_id, status="held")
    assert len(rows) == 1
    assert rows[0].reason_code == REASON_INGRESS_PAUSED
    assert rows[0].shopify_order_id == "55001"


def test_book_failure_records_dlq(db: Session, shopify_shop: ShopifyShop, monkeypatch) -> None:
    settings = _settings()
    monkeypatch.setattr(shopify, "default_pickup_address", MagicMock(return_value=None))
    body = {"id": 55002, "name": "#55002", "shipping_address": {"address1": "1 Main", "city": "Toronto", "zip": "M5V1A1"}}
    with pytest.raises(RuntimeError, match="default_pickup_required"):
        shopify.process_queued_webhook(
            db,
            settings,
            {
                "action": "shopify_orders_create",
                "shop_domain": shopify_shop.shop_domain,
                "topic": "orders/create",
                "raw_body": json.dumps(body),
            },
        )
    rows = list_ingress_dlq(db, shopify_shop.merchant_id, status="open")
    assert len(rows) >= 1
    assert rows[0].reason_code == REASON_MISSING_PICKUP


def test_auto_dispatch_false_holds_booked(db: Session, shopify_shop: ShopifyShop, monkeypatch) -> None:
    shopify_shop.auto_dispatch = False
    db.commit()
    settings = _settings()
    suffix = uuid4().hex[:8]
    order = Order(
        order_number=f"PC-TEST-{suffix}",
        tracking_number=f"TRK-TEST-{suffix}",
        state=OrderState.BOOKED.value,
        merchant_id=shopify_shop.merchant_id,
        order_source=OrderSource.SHOPIFY.value,
        amount_cents=2500,
        pickup={"formatted": "a"},
        dropoff={"formatted": "b"},
        scheduled_at=datetime.now(UTC),
        compliance_metadata={},
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    from porterchain_api.schemas_merchant import AddressInput

    pickup = AddressInput(
        formatted="1 Main St Toronto ON M5V1A1",
        lat=43.6,
        lng=-79.4,
        postal="M5V1A1",
    )

    monkeypatch.setattr(
        shopify._booking,
        "find_by_idempotency_key",
        MagicMock(return_value=None),
    )
    monkeypatch.setattr(shopify._booking, "create_shipment", MagicMock(return_value=order))
    monkeypatch.setattr(shopify, "default_pickup_address", MagicMock(return_value=MagicMock()))
    monkeypatch.setattr(shopify, "assert_ontario_booking", lambda *a, **k: None)
    monkeypatch.setattr(shopify, "_ensure_coords", lambda a: a)
    monkeypatch.setattr(shopify, "address_from_saved", MagicMock(return_value=pickup))
    monkeypatch.setattr(shopify, "_actor", MagicMock(return_value=MagicMock(id="u1")))

    result = shopify._book_from_shopify_payload(
        db,
        settings,
        shop_domain=shopify_shop.shop_domain,
        payload={
            "id": 55003,
            "name": "#55003",
            "shipping_address": {
                "address1": "2 King",
                "city": "Toronto",
                "zip": "M5V2B2",
                "latitude": 43.65,
                "longitude": -79.38,
            },
        },
    )
    assert result.get("held_for_ops") is True
    create_call = shopify._booking.create_shipment
    assert create_call.called
    assert create_call.call_args.kwargs.get("auto_dispatch") is False


def test_release_shopify_order(db: Session, shopify_shop: ShopifyShop, monkeypatch) -> None:
    suffix = uuid4().hex[:8]
    order = Order(
        order_number=f"PC-HOLD-{suffix}",
        tracking_number=f"TRK-HOLD-{suffix}",
        state=OrderState.BOOKED.value,
        merchant_id=shopify_shop.merchant_id,
        order_source=OrderSource.SHOPIFY.value,
        amount_cents=2500,
        pickup={"formatted": "a"},
        dropoff={"formatted": "b"},
        scheduled_at=datetime.now(UTC),
        compliance_metadata={"shopify": {"held_for_ops": True, "shop_domain": shopify_shop.shop_domain}},
        is_sandbox=False,
    )
    db.add(order)
    db.commit()
    db.refresh(order)

    monkeypatch.setattr(
        "porterchain_api.admin_engine.shopify_control_service.transition_to_dispatch_ready",
        lambda db, order, **kw: setattr(order, "state", OrderState.DISPATCH_READY.value),
    )
    monkeypatch.setattr(
        "porterchain_api.admin_engine.shopify_control_service.write_staff_audit",
        MagicMock(),
        raising=False,
    )
    # write_staff_audit is imported inside the function from merchant_org
    with patch(
        "porterchain_api.admin_engine.merchant_org.write_staff_audit",
        MagicMock(),
    ):
        out = release_shopify_order_to_fleetbase(db, _admin_ctx(), order.id)
    assert out["state"] == OrderState.DISPATCH_READY.value
    db.refresh(order)
    assert (order.compliance_metadata or {}).get("shopify", {}).get("held_for_ops") is False


def test_set_ingress_paused_requires_reason(db: Session, shopify_shop: ShopifyShop) -> None:
    with patch(
        "porterchain_api.admin_engine.merchant_org.require_integrations_elevated",
        MagicMock(),
    ), patch(
        "porterchain_api.admin_engine.merchant_org.require_merchant",
        MagicMock(return_value=None),
    ), patch(
        "porterchain_api.admin_engine.merchant_org.write_staff_audit",
        MagicMock(),
    ):
        with pytest.raises(ValueError, match="reason_required"):
            set_ingress_paused(
                db, _admin_ctx(), shopify_shop.merchant_id, shopify_shop.id, paused=True, reason=""
            )
        out = set_ingress_paused(
            db,
            _admin_ctx(),
            shopify_shop.merchant_id,
            shopify_shop.id,
            paused=True,
            reason="ops freeze",
        )
    assert out["ingress_paused"] is True
    db.refresh(shopify_shop)
    assert shopify_shop.ingress_paused is True


def test_set_auto_dispatch(db: Session, shopify_shop: ShopifyShop) -> None:
    with patch(
        "porterchain_api.admin_engine.merchant_org.require_integrations_elevated",
        MagicMock(),
    ), patch(
        "porterchain_api.admin_engine.merchant_org.require_merchant",
        MagicMock(return_value=None),
    ), patch(
        "porterchain_api.admin_engine.merchant_org.write_staff_audit",
        MagicMock(),
    ):
        out = set_auto_dispatch(
            db,
            _admin_ctx(),
            shopify_shop.merchant_id,
            shopify_shop.id,
            enabled=False,
            reason="retail hold",
        )
    assert out["auto_dispatch"] is False
    db.refresh(shopify_shop)
    assert shopify_shop.auto_dispatch is False


def test_control_tower_lists_shopify_dlq(db: Session, shopify_shop: ShopifyShop) -> None:
    from porterchain_api.admin_engine.control_tower.service import ControlTowerService
    from porterchain_api.merchant_engine.shopify_ingress_dlq import record_ingress_dlq

    record_ingress_dlq(
        db,
        shop=shopify_shop,
        shop_domain=shopify_shop.shop_domain,
        action="shopify_orders_create",
        topic="orders/create",
        raw_body='{"id": 99, "name": "#99"}',
        reason_code="missing_pickup",
        detail="default_pickup_required",
        status="open",
    )
    items = ControlTowerService().exceptions(db, limit=50)
    shopify_items = [i for i in items if str(i.get("id", "")).startswith("shopify-dlq:")]
    assert shopify_items
    assert any(i["type"] == "shopify.ingress.missing_pickup" for i in shopify_items)


def test_push_fulfillment_records_silent_error(db: Session, shopify_shop: ShopifyShop) -> None:
    from porterchain_api.merchant_engine.shopify_fulfillment_service import push_fulfillment

    suffix = uuid4().hex[:8]
    order = Order(
        order_number=f"PC-FF-{suffix}",
        tracking_number=f"TRK-FF-{suffix}",
        state=OrderState.IN_TRANSIT.value,
        merchant_id=shopify_shop.merchant_id,
        order_source=OrderSource.SHOPIFY.value,
        amount_cents=2500,
        pickup={"formatted": "a"},
        dropoff={"formatted": "b"},
        scheduled_at=datetime.now(UTC),
        compliance_metadata={"shopify": {"shop_domain": shopify_shop.shop_domain}},
        is_sandbox=False,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    push_fulfillment(db, _settings(), order)
    db.refresh(order)
    err = ((order.compliance_metadata or {}).get("shopify") or {}).get("last_fulfillment_error")
    assert err == "missing_shopify_ids"
