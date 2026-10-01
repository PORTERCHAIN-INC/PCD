"""Shopify buyer access and erasure."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from porterchain_api.booking_models import Address, Order, Stop
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.domain.states import OrderSource, OrderState
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_engine.shopify_privacy import (
    export_for_merchant,
    normalize_phone,
    open_privacy_request,
    process_privacy_request,
)
from porterchain_api.merchant_models import (
    Merchant,
    MerchantUser,
    ShopifyDataSubjectRequest,
    ShopifyIngressDlq,
    ShopifyShop,
)


def _merchant(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Privacy Co {suffix}",
        email=f"privacy-{suffix}@test.local",
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
        shop_domain=f"privacy-{uuid4().hex[:8]}.myshopify.com",
        installed_at=datetime.now(UTC),
        encrypted_access_token="enc-token",
        encrypted_webhook_secret="enc-secret",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _order(db, merchant_id: str, shop_domain: str, *, shopify_order_id: str, phone: str, email: str) -> Order:
    suffix = uuid4().hex[:8]
    order = Order(
        order_number=f"PC{suffix}",
        tracking_number=f"TR{suffix}",
        merchant_id=merchant_id,
        order_source=OrderSource.SHOPIFY.value,
        amount_cents=1200,
        currency="cad",
        scheduled_at=datetime.now(UTC),
        pickup={"formatted": "Warehouse", "postal": "L4Z1S6"},
        dropoff={
            "formatted": "1 King St W, Toronto",
            "name": "Ada",
            "phone": phone,
            "address1": "1 King St W",
            "postal": "M5V 2T6",
            "city": "Toronto",
            "lat": 43.6,
            "lng": -79.3,
        },
        special_instructions="Leave at the blue door",
        compliance_metadata={
            "shopify": {
                "shop_domain": shop_domain,
                "order_id": shopify_order_id,
                "customer": {"id": "9", "email": email, "phone": phone, "name": "Ada"},
            }
        },
    )
    db.add(order)
    db.flush()
    address = Address(
        formatted="1 King St W, Toronto",
        line1="1 King St W",
        postal="M5V 2T6",
        city="Toronto",
        contact_name="Ada",
        phone=phone,
        lat=43.6,
        lng=-79.3,
    )
    db.add(address)
    db.flush()
    db.add(Stop(order_id=order.id, sequence=1, kind="drop", address_id=address.id))
    db.add(
        ShopifyIngressDlq(
            merchant_id=merchant_id,
            shop_domain=shop_domain,
            action="book",
            reason_code="worker_error",
            shopify_order_id=shopify_order_id,
            raw_body=json.dumps({"email": email, "phone": phone}),
        )
    )
    db.commit()
    db.refresh(order)
    return order


def test_normalize_phone_matches_local_and_e164() -> None:
    assert normalize_phone("416 555 0100") == normalize_phone("+14165550100")
    assert normalize_phone("416 555 0100") == "+14165550100"


def test_data_request_ack_has_no_buyer_contact_and_is_idempotent(db, settings) -> None:
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    body = json.dumps(
        {
            "shop_domain": shop.shop_domain,
            "customer": {"id": 9, "email": "ada@example.com", "phone": "+14165550100"},
            "orders_requested": [1001],
        }
    ).encode()
    webhook_id = f"wh-{uuid4().hex}"
    first = open_privacy_request(
        db, topic="customers/data_request", shop=shop, raw_body=body, webhook_id=webhook_id
    )
    encoded = json.dumps(first)
    assert "ada@example.com" not in encoded
    assert "416" not in encoded
    assert first["request_id"]
    second = open_privacy_request(
        db, topic="customers/data_request", shop=shop, raw_body=body, webhook_id=webhook_id
    )
    assert second.get("retry") is True
    assert (
        db.query(ShopifyDataSubjectRequest)
        .filter(ShopifyDataSubjectRequest.shopify_webhook_id == webhook_id)
        .count()
        == 1
    )
    done = process_privacy_request(db, settings, first["request_id"])
    assert done["status"] == "fulfilled"
    again = open_privacy_request(
        db, topic="customers/data_request", shop=shop, raw_body=body, webhook_id=webhook_id
    )
    assert again.get("duplicate") is True


def test_orders_to_redact_clears_street_email_and_dlq(db, settings) -> None:
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    target = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="older-1",
        phone="416 555 0100",
        email="ada@example.com",
    )
    other = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="newer-2",
        phone="416 555 0199",
        email="ada@example.com",
    )
    target.created_at = datetime.now(UTC) - timedelta(days=800)
    db.commit()
    body = json.dumps(
        {
            "customer": {"id": 9, "email": "ada@example.com", "phone": "+14165550100"},
            "orders_to_redact": ["older-1"],
        }
    ).encode()
    opened = open_privacy_request(
        db, topic="customers/redact", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    process_privacy_request(db, settings, opened["request_id"])
    db.refresh(target)
    db.refresh(other)
    assert target.dropoff["formatted"] is None
    assert target.dropoff["postal"] == "M5V"
    assert target.compliance_metadata["shopify"]["customer"]["email"] is None
    assert target.special_instructions is None
    assert other.compliance_metadata["shopify"]["customer"]["email"] == "ada@example.com"
    rows = (
        db.query(ShopifyIngressDlq)
        .filter(
            ShopifyIngressDlq.merchant_id == ctx.merchant.id,
            ShopifyIngressDlq.shopify_order_id == "older-1",
        )
        .all()
    )
    assert rows
    assert all(row.raw_body == "" for row in rows)
    stop = db.query(Stop).filter(Stop.order_id == target.id).one()
    address = db.get(Address, stop.address_id)
    assert address.formatted == "redacted"
    assert address.phone is None


def test_phone_match_without_order_list(db, settings) -> None:
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    order = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="phone-1",
        phone="416 555 0100",
        email="ada@example.com",
    )
    body = json.dumps({"customer": {"phone": "+14165550100"}}).encode()
    opened = open_privacy_request(
        db, topic="customers/redact", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    result = process_privacy_request(db, settings, opened["request_id"])
    assert result["orders"] == 1
    db.refresh(order)
    assert order.compliance_metadata["shopify"]["customer"]["phone"] is None


def test_open_chargeback_keeps_postal(db, settings) -> None:
    from porterchain_api.admin_models import Claim

    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    order = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="cb-1",
        phone="+14165550100",
        email="ada@example.com",
    )
    db.add(
        Claim(
            order_id=order.id,
            merchant_id=ctx.merchant.id,
            claim_type="chargeback",
            status="open",
        )
    )
    db.commit()
    body = json.dumps({"orders_to_redact": ["cb-1"], "customer": {"email": "ada@example.com"}}).encode()
    opened = open_privacy_request(
        db, topic="customers/redact", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    process_privacy_request(db, settings, opened["request_id"])
    db.refresh(order)
    row = db.get(ShopifyDataSubjectRequest, opened["request_id"])
    assert row.status == "partial_hold"
    assert row.hold_reason == "chargeback"
    assert order.dropoff["formatted"] is None
    assert order.dropoff["postal"] == "M5V 2T6"


def test_held_order_keeps_postal(db, settings) -> None:
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    order = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="tax-1",
        phone="+14165550100",
        email="ada@example.com",
    )
    order.state = OrderState.INVOICED.value
    db.commit()
    body = json.dumps({"orders_to_redact": ["tax-1"], "customer": {"email": "ada@example.com"}}).encode()
    opened = open_privacy_request(
        db, topic="customers/redact", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    process_privacy_request(db, settings, opened["request_id"])
    db.refresh(order)
    row = db.get(ShopifyDataSubjectRequest, opened["request_id"])
    assert row.status == "partial_hold"
    assert row.hold_reason == "tax"
    assert order.dropoff["formatted"] is None
    assert order.dropoff["postal"] == "M5V 2T6"


def test_shop_redact_clears_token_and_buyer_slice(db, settings) -> None:
    ctx = _merchant(db)
    shop = _shop(db, ctx.merchant.id)
    order = _order(
        db,
        ctx.merchant.id,
        shop.shop_domain,
        shopify_order_id="shop-1",
        phone="+14165550100",
        email="ada@example.com",
    )
    body = json.dumps({"shop_domain": shop.shop_domain}).encode()
    opened = open_privacy_request(
        db, topic="shop/redact", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    process_privacy_request(db, settings, opened["request_id"])
    db.refresh(shop)
    db.refresh(order)
    assert shop.encrypted_access_token is None
    assert order.dropoff["name"] is None


def test_other_merchant_cannot_download_export(db, settings) -> None:
    owner = _merchant(db)
    shop = _shop(db, owner.merchant.id)
    _order(
        db,
        owner.merchant.id,
        shop.shop_domain,
        shopify_order_id="exp-1",
        phone="+14165550100",
        email="ada@example.com",
    )
    body = json.dumps(
        {"customer": {"email": "ada@example.com"}, "orders_requested": ["exp-1"]}
    ).encode()
    opened = open_privacy_request(
        db, topic="customers/data_request", shop=shop, raw_body=body, webhook_id=f"wh-{uuid4().hex}"
    )
    process_privacy_request(db, settings, opened["request_id"])
    other = _merchant(db)
    assert (
        export_for_merchant(
            db, settings, merchant_id=other.merchant.id, request_id=opened["request_id"]
        )
        is None
    )
    from unittest.mock import patch

    from fastapi import HTTPException

    from porterchain_api.routers.merchant import privacy as privacy_routes

    with patch.object(privacy_routes, "require_module"):
        try:
            privacy_routes.shopify_privacy_export(opened["request_id"], other, db, settings)
        except HTTPException as exc:
            assert exc.status_code == 404
            return
    raise AssertionError("expected 404")
