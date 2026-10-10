"""Phase 4: Shopify webhook HMAC → enqueue; 401/503/200; cancel topic."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine import shopify_webhooks
from porterchain_api.merchant_engine import shopify_payload_ops
from porterchain_api.merchant_models import Merchant, ShopifyShop


def _hmac(body: bytes, secret: str) -> str:
    return base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()


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
        company_name=f"Shop Co {suffix}",
        email=f"shop-{suffix}@test.invalid",
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    row = ShopifyShop(
        merchant_id=merchant.id,
        shop_domain=f"acme-{suffix}.myshopify.com",
        scopes="read_orders,write_fulfillments",
        installed_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_ingest_bad_hmac_raises_permission(db: Session, shopify_shop: ShopifyShop) -> None:
    settings = _settings()
    body = b'{"id":1}'
    with pytest.raises(PermissionError, match="shopify_hmac_invalid"):
        shopify_webhooks.ingest_webhook(
            db,
            settings,
            raw_body=body,
            hmac_header="bad",
            shop_domain_header=shopify_shop.shop_domain,
            topic="orders/create",
        )


def test_ingest_orders_create_enqueues_and_returns_queued(
    db: Session, shopify_shop: ShopifyShop
) -> None:
    settings = _settings()
    body = json.dumps({"id": 4242, "name": "#42"}).encode()
    header = _hmac(body, settings.shopify_api_secret)
    mock_pub = MagicMock()
    with patch(
        "porterchain_shared.queue.publisher.get_queue_publisher",
        return_value=mock_pub,
    ):
        result = shopify_webhooks.ingest_webhook(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain_header=shopify_shop.shop_domain,
            topic="orders/create",
        )
    assert result["ok"] is True
    assert result["queued"] is True
    assert result["action"] == "shopify_orders_create"
    mock_pub.enqueue.assert_called_once()
    args, kwargs = mock_pub.enqueue.call_args
    payload = args[1] if len(args) > 1 else kwargs.get("payload")
    assert payload["action"] == "shopify_orders_create"
    assert payload["shop_domain"] == shopify_shop.shop_domain


def test_ingest_enqueue_failure_raises_for_503(db: Session, shopify_shop: ShopifyShop) -> None:
    settings = _settings()
    body = b'{"id":99}'
    header = _hmac(body, settings.shopify_api_secret)
    mock_pub = MagicMock()
    mock_pub.enqueue.side_effect = ConnectionError("redis down")
    with (
        patch("porterchain_shared.queue.publisher.get_queue_publisher", return_value=mock_pub),
        pytest.raises(RuntimeError, match="shopify_enqueue_failed"),
    ):
        shopify_webhooks.ingest_webhook(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain_header=shopify_shop.shop_domain,
            topic="orders/create",
        )


def test_ingest_orders_cancelled_enqueues(db: Session, shopify_shop: ShopifyShop) -> None:
    settings = _settings()
    body = json.dumps({"id": 77, "name": "#77"}).encode()
    header = _hmac(body, settings.shopify_api_secret)
    mock_pub = MagicMock()
    with patch(
        "porterchain_shared.queue.publisher.get_queue_publisher",
        return_value=mock_pub,
    ):
        result = shopify_webhooks.ingest_webhook(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain_header=shopify_shop.shop_domain,
            topic="orders/cancelled",
        )
    assert result["action"] == "shopify_orders_cancelled"
    mock_pub.enqueue.assert_called_once()


def test_cancel_from_payload_skips_missing_order(db: Session, shopify_shop: ShopifyShop) -> None:
    settings = _settings()
    result = shopify_payload_ops._cancel_from_shopify_payload(
        db,
        settings,
        shop_domain=shopify_shop.shop_domain,
        payload={"id": 999001, "name": "#x"},
    )
    assert result.get("skipped") == "order_not_found"


def test_book_idempotent_replay(db: Session, shopify_shop: ShopifyShop, monkeypatch) -> None:
    """Worker book path: second call with same key returns replayed."""
    settings = _settings()
    # Skip Ontario/Valhalla-heavy create — stub find + create
    order = MagicMock(id="ord-1", tracking_number="TRK1", compliance_metadata={})
    monkeypatch.setattr(
        shopify._booking,
        "find_by_idempotency_key",
        MagicMock(side_effect=[None, order]),
    )
    monkeypatch.setattr(shopify._booking, "create_shipment", MagicMock(return_value=order))
    monkeypatch.setattr(
        shopify,
        "default_pickup_address",
        MagicMock(
            return_value=MagicMock(
                formatted="1 Main St Toronto ON",
                postal="M5V1A1",
                lat=43.6,
                lng=-79.4,
                line1="1 Main",
                city="Toronto",
                region="ON",
                country="CA",
            )
        ),
    )
    monkeypatch.setattr(shopify, "assert_ontario_booking", lambda *a, **k: None)
    monkeypatch.setattr(shopify, "_ensure_coords", lambda a: a)
    monkeypatch.setattr(
        shopify,
        "address_from_saved",
        lambda row: __import__(
            "porterchain_api.schemas_merchant", fromlist=["AddressInput"]
        ).AddressInput(formatted=row.formatted, postal=row.postal, lat=row.lat, lng=row.lng),
    )
    monkeypatch.setattr(
        shopify,
        "_actor",
        MagicMock(return_value=MagicMock(id="u1")),
    )

    payload = {
        "id": 555,
        "name": "#555",
        "shipping_address": {
            "address1": "1 King",
            "city": "Toronto",
            "province_code": "ON",
            "zip": "M5V2T6",
            "latitude": 43.65,
            "longitude": -79.38,
        },
        "line_items": [{"grams": 1000, "quantity": 1}],
    }
    first = shopify_payload_ops._book_from_shopify_payload(
        db, settings, shop_domain=shopify_shop.shop_domain, payload=payload
    )
    assert first["order_id"] == "ord-1"
    # Second: find returns existing immediately
    shopify._booking.find_by_idempotency_key = MagicMock(return_value=order)
    second = shopify_payload_ops._book_from_shopify_payload(
        db, settings, shop_domain=shopify_shop.shop_domain, payload=payload
    )
    assert second.get("replayed") is True


def test_shopify_webhook_router_http_401_503_200(db: Session, shopify_shop: ShopifyShop) -> None:
    """P4.2: router maps ingest failures to HTTP 401 / 503 / 200."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from porterchain_api.config import get_settings
    from porterchain_api.db import get_db
    from porterchain_api.routers.shopify import router

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: _settings()
    client = TestClient(app)
    body = b'{"id":55}'
    headers = {
        "X-Shopify-Shop-Domain": shopify_shop.shop_domain,
        "X-Shopify-Topic": "orders/create",
        "Content-Type": "application/json",
    }

    bad = client.post(
        "/v1/integrations/shopify/webhooks",
        content=body,
        headers={**headers, "X-Shopify-Hmac-Sha256": "bad"},
    )
    assert bad.status_code == 401

    with patch(
        "porterchain_api.routers.shopify.webhook_ingress.ingest_webhook",
        side_effect=RuntimeError("shopify_enqueue_failed"),
    ):
        fail = client.post(
            "/v1/integrations/shopify/webhooks",
            content=body,
            headers={**headers, "X-Shopify-Hmac-Sha256": "x"},
        )
    assert fail.status_code == 503

    with patch(
        "porterchain_api.routers.shopify.webhook_ingress.ingest_webhook",
        return_value={"ok": True, "queued": True},
    ):
        ok = client.post(
            "/v1/integrations/shopify/webhooks",
            content=body,
            headers={**headers, "X-Shopify-Hmac-Sha256": "x"},
        )
    assert ok.status_code == 200
    assert ok.json().get("ok") is True
