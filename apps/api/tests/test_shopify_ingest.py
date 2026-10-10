"""Shopify HMAC, shop domain, and orders/create mapping."""

from datetime import UTC, datetime

from porterchain_api.integrations.shopify_hmac import (
    verify_oauth_hmac,
    verify_webhook_hmac,
)
from porterchain_api.integrations.shopify_orders import map_shopify_order
from porterchain_api.merchant_engine.shopify_service import (
    is_shop_domain,
    normalize_shop_domain,
)
from porterchain_api.schemas_merchant import AddressInput


def test_normalize_shop_domain() -> None:
    assert normalize_shop_domain("https://Acme-Store.myshopify.com/admin") == "acme-store.myshopify.com"
    assert normalize_shop_domain("acme-store") == "acme-store.myshopify.com"
    assert is_shop_domain("acme-store.myshopify.com")
    assert not is_shop_domain("evil.example.com")


def test_webhook_hmac_accepts_matching_secret() -> None:
    body = b'{"id":1}'
    secret = "shpss_test"
    import base64
    import hashlib
    import hmac

    header = base64.b64encode(hmac.new(secret.encode(), body, hashlib.sha256).digest()).decode()
    assert verify_webhook_hmac(body, header, [secret]) is True
    assert verify_webhook_hmac(body, header, ["other"]) is False
    assert verify_webhook_hmac(body, None, [secret]) is False


def test_oauth_hmac_sorted_query() -> None:
    secret = "shpss_oauth"
    import hashlib
    import hmac

    message = "shop=acme.myshopify.com&timestamp=1"
    digest = hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()
    query = f"hmac={digest}&shop=acme.myshopify.com&timestamp=1"
    assert verify_oauth_hmac(query, secret) is True
    assert verify_oauth_hmac(query, "wrong") is False


def test_map_shopify_order_copies_postal_and_weight() -> None:
    pickup = AddressInput(formatted="100 Britannia Rd E, Mississauga ON L4Z 1S3", postal="L4Z 1S3", lat=43.6, lng=-79.6)
    payload = {
        "id": 999001,
        "name": "#1001",
        "shipping_address": {
            "address1": "1 King St W",
            "city": "Toronto",
            "province_code": "ON",
            "zip": "M5V 2T6",
            "latitude": 43.6488,
            "longitude": -79.3817,
            "name": "Ada",
            "phone": "4165550100",
        },
        "line_items": [{"grams": 2500, "quantity": 2}],
    }
    body = map_shopify_order(payload, pickup=pickup)
    assert body.dropoff.postal == "M5V 2T6"
    assert body.dropoff.lat == 43.6488
    assert body.internal_reference == "#1001"
    assert body.purchase_order_number == "999001"
    assert body.weight_kg == 5.0
    assert isinstance(body.scheduled_at, datetime)
    assert body.scheduled_at.tzinfo == UTC


def test_map_shopify_order_requires_shipping_address() -> None:
    pickup = AddressInput(formatted="warehouse")
    try:
        map_shopify_order({"id": 1, "line_items": []}, pickup=pickup)
    except ValueError as exc:
        assert str(exc) == "shipping_address_required"
        return
    raise AssertionError("expected shipping_address_required")
