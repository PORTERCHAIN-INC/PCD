"""HS-19 — Shopify webhook → WEBHOOKS queue → create/cancel shipment path."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from porterchain_shared.queue.names import QueueName
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_models import Merchant, ShopifyShop


@pytest.fixture
def webhooks_module():
    import sys
    from pathlib import Path

    worker_root = Path(__file__).resolve().parents[2] / "worker"
    if str(worker_root) not in sys.path:
        sys.path.insert(0, str(worker_root))
    from processors import webhooks

    return webhooks


def _settings(**overrides) -> Settings:
    base = dict(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        shopify_api_secret="shpss_hs19",
        fleetbase_dispatch_bridge=False,
    )
    base.update(overrides)
    return Settings(**base)


@pytest.fixture
def shopify_shop(db: Session) -> ShopifyShop:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name=f"HS19 Shop {suffix}",
        email=f"hs19-{suffix}@test.invalid",
        payment_terms="NET_30",
        profile={},
    )
    db.add(merchant)
    db.flush()
    row = ShopifyShop(
        merchant_id=merchant.id,
        shop_domain=f"hs19-{suffix}.myshopify.com",
        scopes="read_orders,write_fulfillments",
        installed_at=datetime.now(UTC),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_hs19_process_queued_webhook_routes_create_and_cancel(db: Session) -> None:
    settings = _settings()
    create_payload = {
        "action": "shopify_orders_create",
        "shop_domain": "hs19.myshopify.com",
        "raw_body": json.dumps({"id": 1001, "name": "#1001"}),
    }
    cancel_payload = {
        "action": "shopify_orders_cancelled",
        "shop_domain": "hs19.myshopify.com",
        "raw_body": json.dumps({"id": 1001, "name": "#1001"}),
    }
    with (
        patch.object(shopify, "_book_from_shopify_payload", return_value={"booked": True}) as book,
        patch.object(shopify, "_cancel_from_shopify_payload", return_value={"cancelled": True}) as cancel,
    ):
        assert shopify.process_queued_webhook(db, settings, create_payload) == {"booked": True}
        book.assert_called_once()
        assert shopify.process_queued_webhook(db, settings, cancel_payload) == {"cancelled": True}
        cancel.assert_called_once()

    with pytest.raises(ValueError, match="unknown_shopify_action"):
        shopify.process_queued_webhook(
            db,
            settings,
            {"action": "shopify_unknown", "shop_domain": "x", "raw_body": "{}"},
        )


def test_hs19_worker_process_webhook_invokes_queued_processor(webhooks_module) -> None:
    payload = {
        "action": "shopify_orders_create",
        "shop_domain": "hs19.myshopify.com",
        "raw_body": "{}",
    }
    with patch(
        "porterchain_api.merchant_engine.shopify_service.process_queued_webhook",
        return_value={"ok": True},
    ) as queued:
        with patch("porterchain_api.db.SessionLocal") as session_local:
            session_local.return_value = MagicMock()
            webhooks_module.process_webhook(payload)
        queued.assert_called_once()
        assert queued.call_args.args[2]["action"] == "shopify_orders_create"


def test_hs19_worker_reraises_so_queue_can_retry(webhooks_module) -> None:
    payload = {
        "action": "shopify_orders_cancelled",
        "shop_domain": "hs19.myshopify.com",
        "raw_body": "{}",
    }
    with patch(
        "porterchain_api.merchant_engine.shopify_service.process_queued_webhook",
        side_effect=RuntimeError("hs19_book_failed"),
    ), patch("porterchain_api.db.SessionLocal") as session_local:
        db = MagicMock()
        session_local.return_value = db
        with pytest.raises(RuntimeError, match="hs19_book_failed"):
            webhooks_module.process_webhook(payload)
        db.rollback.assert_called()


def test_hs19_ingest_enqueue_shape_matches_worker(db: Session, shopify_shop: ShopifyShop) -> None:
    """ingest_webhook enqueue payload must be process_queued_webhook-compatible."""
    settings = _settings()
    body = json.dumps({"id": 19, "name": "#HS19"}).encode()
    header = base64.b64encode(
        hmac.new(settings.shopify_api_secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    mock_pub = MagicMock()
    with patch(
        "porterchain_shared.queue.publisher.get_queue_publisher",
        return_value=mock_pub,
    ):
        out = shopify.ingest_webhook(
            db,
            settings,
            raw_body=body,
            hmac_header=header,
            shop_domain_header=shopify_shop.shop_domain,
            topic="orders/create",
        )
    assert out["queued"] is True
    args, _kwargs = mock_pub.enqueue.call_args
    assert args[0] == QueueName.WEBHOOKS
    job = args[1]
    assert job["action"] == "shopify_orders_create"
    assert job["shop_domain"] == shopify_shop.shop_domain
    assert "raw_body" in job
    with patch.object(shopify, "_book_from_shopify_payload", return_value={"booked": True}):
        assert shopify.process_queued_webhook(db, settings, job)["booked"] is True
