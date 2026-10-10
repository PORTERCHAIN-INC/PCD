"""Shopify shop pickup binds to the merchant warehouse, not a second manual step."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock
from uuid import uuid4

from porterchain_api.admin_engine.merchant360_board import api_keys_payload
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.profile_service import MerchantProfileService
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.shopify_service import default_pickup_address
from porterchain_api.merchant_models import Merchant, MerchantUser, SavedAddress, ShopifyShop


def _merchant(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Pickup Co {suffix}",
        email=f"pickup-{suffix}@test.local",
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


def _shop(db, merchant_id: str) -> ShopifyShop:
    row = ShopifyShop(
        merchant_id=merchant_id,
        shop_domain=f"bind-{uuid4().hex[:8]}.myshopify.com",
        installed_at=datetime.now(UTC),
        encrypted_access_token="enc",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_address_saved_after_install_binds_shop(db):
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    record = MerchantProfileService().create_saved_address(
        db,
        ctx,
        label="Warehouse",
        address_type="pickup",
        formatted="91 Breton Ave, Mississauga, ON L4Z 4K5",
        is_default=True,
    )
    db.refresh(shop)
    assert shop.default_pickup_address_id == record.id


def test_admin_missing_pickup_follows_warehouse_not_shop_column(db):
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    db.add(
        SavedAddress(
            merchant_id=ctx.merchant.id,
            label="Warehouse",
            address_type="pickup",
            formatted="91 Breton Ave, Mississauga, ON L4Z 4K5",
            is_default=True,
        )
    )
    db.commit()
    payload = api_keys_payload(db, ctx.merchant.id)
    row = payload["shopify_shops"][0]
    assert row["id"] == shop.id
    assert row["default_pickup_address_id"] is None
    assert row["default_pickup"] == "91 Breton Ave, Mississauga, ON L4Z 4K5"
    assert row["missing_pickup"] is False
    assert row["carrier_registered"] is False
    assert row["fulfillment_service_registered"] is False


def test_dropoff_is_not_a_shopify_pickup(db):
    ctx = _merchant(db)
    _shop(db, ctx.merchant.id)
    db.add(
        SavedAddress(
            merchant_id=ctx.merchant.id,
            label="Customer",
            address_type="dropoff",
            formatted="2 King St, Toronto",
            is_default=True,
        )
    )
    db.commit()
    assert default_pickup_address(db, ctx.merchant.id) is None
    row = api_keys_payload(db, ctx.merchant.id)["shopify_shops"][0]
    assert row["missing_pickup"] is True
    assert row["default_pickup"] is None


def test_book_path_fills_null_shop_pickup(db, settings, monkeypatch):
    from porterchain_api.merchant_engine import shopify_service as shopify
    from porterchain_api.merchant_engine import shopify_payload_ops

    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    addr = SavedAddress(
        merchant_id=ctx.merchant.id,
        label="Warehouse",
        address_type="pickup",
        formatted="91 Breton Ave, Mississauga, ON L4Z 4K5",
        lat=43.6,
        lng=-79.6,
        postal="L4Z4K5",
        is_default=True,
    )
    db.add(addr)
    db.commit()
    order = MagicMock()
    order.id = "order-1"
    order.compliance_metadata = {}
    monkeypatch.setattr(shopify, "_ensure_coords", lambda value: value)
    monkeypatch.setattr(
        "porterchain_api.merchant_engine.shopify_payload_ops.assert_ontario_booking",
        lambda *a, **k: None,
    )
    monkeypatch.setattr(shopify, "_actor", MagicMock(return_value=ctx.user))
    monkeypatch.setattr(shopify._booking, "find_by_idempotency_key", MagicMock(return_value=None))
    monkeypatch.setattr(shopify._booking, "create_shipment", MagicMock(return_value=order))

    shopify_payload_ops._book_from_shopify_payload(
        db,
        settings,
        shop_domain=shop.shop_domain,
        payload={
            "id": 88001,
            "financial_status": "paid",
            "shipping_address": {
                "address1": "2 King",
                "city": "Toronto",
                "country": "Canada",
                "zip": "M5V2B2",
                "latitude": 43.65,
                "longitude": -79.38,
            },
        },
    )
    db.refresh(shop)
    assert shop.default_pickup_address_id == addr.id


def test_webhook_register_failure_is_reported(db, settings, monkeypatch):
    from porterchain_api.merchant_engine import shopify_fulfillment_ops as ops
    from porterchain_api.merchant_engine import shopify_service as shopify

    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    monkeypatch.setattr(shopify, "_decrypt", lambda *a, **k: "token")
    monkeypatch.setattr(shopify, "_admin_get", lambda *a, **k: {"webhooks": []})
    monkeypatch.setattr(shopify, "_admin_post", lambda *a, **k: None)
    monkeypatch.setattr(ops, "_register_carrier_service", lambda *a, **k: None)
    monkeypatch.setattr(ops, "_register_fulfillment_service", lambda *a, **k: None)

    result = ops.re_register_shop_hooks(shop, settings)
    assert result["ok"] is False
    assert any(err.startswith("webhooks:") for err in result["errors"])
