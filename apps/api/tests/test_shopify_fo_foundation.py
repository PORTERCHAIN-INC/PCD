"""Flag-gated Shopify FulfillmentService foundation (accept→book still held)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from porterchain_api.config import Settings
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine import shopify_webhooks
from porterchain_api.merchant_engine.shopify_urls import fulfillment_service_url


def _settings(*, fo: bool = False) -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        porterchain_api_url="https://api.porterchain.com",
        merchant_portal_url="https://merchant.porterchain.com",
        shopify_api_key="cid",
        shopify_api_secret="shpss_test",
        shopify_fulfillment_service_enabled=fo,
        fleetbase_dispatch_bridge=False,
    )


def test_fulfillment_service_url() -> None:
    assert fulfillment_service_url(_settings()).endswith(
        "/v1/integrations/shopify/fs/fulfillment_order_notification"
    )


def test_fo_notification_ignored_when_flag_off() -> None:
    result = shopify.ingest_fulfillment_order_notification(
        MagicMock(),
        _settings(fo=False),
        raw_body=b"{}",
        hmac_header=None,
        shop_domain_header="acme.myshopify.com",
    )
    assert result == {"ok": True, "ignored": True, "reason": "fo_flag_off"}


def test_fo_webhook_ignored_when_flag_off() -> None:
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with patch(
        "porterchain_api.merchant_engine.shopify_webhooks.verify_webhook_hmac",
        return_value=True,
    ):
        result = shopify_webhooks.ingest_webhook(
            db,
            _settings(fo=False),
            raw_body=b"{}",
            hmac_header="ok",
            shop_domain_header="acme.myshopify.com",
            topic="fulfillment_orders/fulfillment_request_submitted",
        )
    assert result["ignored"] == "fulfillment/orders/fulfillment/request/submitted"
    assert result.get("reason") == "fo_flag_off"


def test_process_queued_fo_stub_when_flag_on() -> None:
    result = shopify_webhooks.process_queued_webhook(
        MagicMock(),
        _settings(fo=True),
        {
            "action": "shopify_fo_request",
            "shop_domain": "acme.myshopify.com",
            "raw_body": '{"kind":"FULFILLMENT_REQUEST"}',
        },
    )
    assert result["skipped"] == "shop_not_connected"
    assert result["action"] == "shopify_fo_request"


def test_process_queued_fo_skipped_when_flag_off() -> None:
    result = shopify_webhooks.process_queued_webhook(
        MagicMock(),
        _settings(fo=False),
        {
            "action": "shopify_fo_request",
            "shop_domain": "acme.myshopify.com",
            "raw_body": "{}",
        },
    )
    assert result == {
        "ok": True,
        "skipped": "fo_flag_off",
        "action": "shopify_fo_request",
    }


def test_post_install_registers_fs_only_when_flag_on() -> None:
    shop = MagicMock()
    shop.shop_domain = "acme.myshopify.com"
    shop.encrypted_access_token = "enc"
    with (
        patch(
            "porterchain_api.merchant_engine.shopify_fulfillment_ops.access_token_for",
            return_value="tok",
        ),
        patch(
            "porterchain_api.merchant_engine.shopify_service._admin_post"
        ) as post,
        patch(
            "porterchain_api.merchant_engine.shopify_fulfillment_service._register_webhooks"
        ),
        patch(
            "porterchain_api.merchant_engine.shopify_fulfillment_service._register_carrier_service"
        ),
    ):
        shopify._post_install_hooks(shop, _settings(fo=False))
        assert post.call_count == 0
        shopify._post_install_hooks(shop, _settings(fo=True))
        paths = [c.args[2] for c in post.call_args_list]
        assert "/fulfillment_services.json" in paths
