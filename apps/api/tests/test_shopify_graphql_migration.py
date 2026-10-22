"""REST Admin API → GraphQL migration: mocked Shopify GraphQL responses only."""

from __future__ import annotations

import ast
import pathlib
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from porterchain_api.merchant_engine import shopify_admin_graphql as gql

S = SimpleNamespace(shopify_api_version="2026-07")
URI = "https://api.porterchain.com/v1/integrations/shopify/webhooks"


def _resp(data: dict, status: int = 200) -> MagicMock:
    r = MagicMock(status_code=status, text="")
    r.json.return_value = {"data": data}
    return r


class _Shopify:
    """Fake GraphQL endpoint: answers by operation name and records every request."""

    def __init__(self, answers: dict):
        self.answers = answers
        self.requests: list[dict] = []

    def post(self, url, headers=None, json=None):
        assert url.endswith("/admin/api/2026-07/graphql.json")
        assert "/admin/api/2026-07/" in url and ".json" in url
        self.requests.append(json)
        q = json["query"]
        for key, val in self.answers.items():
            if key in q:
                return _resp(val(json["variables"]) if callable(val) else val)
        raise AssertionError(f"unexpected query {q[:80]}")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _client(fake):
    return patch(
        "porterchain_api.merchant_engine.shopify_admin_graphql.httpx.Client",
        return_value=fake,
    )


def test_topic_enum_mapping() -> None:
    assert gql.webhook_topic_enum("orders/create") == "ORDERS_CREATE"
    assert gql.webhook_topic_enum("app/uninstalled") == "APP_UNINSTALLED"
    assert (
        gql.webhook_topic_enum("fulfillment_orders/order_routing_complete")
        == "FULFILLMENT_ORDERS_ORDER_ROUTING_COMPLETE"
    )
    assert gql.webhook_topic_enum("RETURNS_APPROVE") == "RETURNS_APPROVE"


def test_webhook_sync_is_idempotent_and_keeps_existing_rest_subscriptions() -> None:
    # Two subscriptions already exist (created earlier by REST) for our URI; one for another URI.
    listed = {
        "webhookSubscriptions": {
            "nodes": [
                {"topic": "ORDERS_CREATE", "uri": URI},
                {"topic": "APP_UNINSTALLED", "uri": URI},
                {"topic": "ORDERS_PAID", "uri": "https://elsewhere.example/hook"},
            ],
            "pageInfo": {"hasNextPage": False, "endCursor": None},
        }
    }
    created = {
        "webhookSubscriptionCreate": {
            "webhookSubscription": {"id": "gid://x/1"},
            "userErrors": [],
        }
    }
    fake = _Shopify({"PcdWebhooksAll": listed, "PcdWebhookCreate": created})
    topics = [
        "orders/create",
        "orders/paid",
        "app/uninstalled",
        "customers/redact",
        "shop/redact",
    ]
    with _client(fake):
        failed = gql.webhook_subscriptions_sync(
            "s.myshopify.com", "tok", S, topics=topics, uri=URI
        )
    assert failed == []
    made = [
        r["variables"]["topic"]
        for r in fake.requests
        if "PcdWebhookCreate" in r["query"]
    ]
    # Existing ones untouched, compliance topics never subscribed at runtime.
    assert made == ["ORDERS_PAID"]
    assert fake.requests[-1]["variables"]["sub"] == {"uri": URI, "format": "JSON"}


def test_webhook_sync_reports_failed_topics_without_raising() -> None:
    listed = {"webhookSubscriptions": {"nodes": [], "pageInfo": {"hasNextPage": False}}}
    err = {
        "webhookSubscriptionCreate": {
            "webhookSubscription": None,
            "userErrors": [{"message": "bad"}],
        }
    }
    fake = _Shopify({"PcdWebhooksAll": listed, "PcdWebhookCreate": err})
    with _client(fake):
        failed = gql.webhook_subscriptions_sync(
            "s.myshopify.com", "tok", S, topics=["orders/create"], uri=URI
        )
    assert failed == ["orders/create"]


def test_webhook_sync_pages_through_subscriptions() -> None:
    pages = iter(
        [
            {
                "webhookSubscriptions": {
                    "nodes": [{"topic": "ORDERS_CREATE", "uri": URI}],
                    "pageInfo": {"hasNextPage": True, "endCursor": "c1"},
                }
            },
            {
                "webhookSubscriptions": {
                    "nodes": [{"topic": "ORDERS_PAID", "uri": URI}],
                    "pageInfo": {"hasNextPage": False},
                }
            },
        ]
    )
    fake = _Shopify({"PcdWebhooksAll": lambda v: next(pages)})
    with _client(fake):
        failed = gql.webhook_subscriptions_sync(
            "s.myshopify.com",
            "tok",
            S,
            topics=["orders/create", "orders/paid"],
            uri=URI,
        )
    assert failed == []
    assert [r["variables"]["after"] for r in fake.requests] == [None, "c1"]


def test_shop_details_maps_to_rest_shape() -> None:
    data = {
        "shop": {
            "id": "gid://shopify/Shop/42",
            "name": "PCDC",
            "email": "a@x.test",
            "contactEmail": "owner@x.test",
            "primaryDomain": {"host": "pcdc.example"},
            "billingAddress": {
                "address1": "100 King St W",
                "address2": None,
                "city": "Toronto",
                "province": "Ontario",
                "provinceCode": "ON",
                "zip": "M5X 1A9",
                "countryCodeV2": "CA",
                "latitude": 43.6,
                "longitude": -79.3,
                "phone": "+14165550100",
            },
        }
    }
    with _client(_Shopify({"PcdShop": data})):
        out = gql.shop_details("s.myshopify.com", "tok", S)
    assert out["id"] == "42"
    assert out["email"] == "owner@x.test"
    assert out["province_code"] == "ON" and out["country_code"] == "CA"
    assert out["domain"] == "pcdc.example" and out["phone"] == "+14165550100"


def test_order_fulfillment_orders_and_multi_create() -> None:
    fos = {
        "order": {
            "fulfillmentOrders": {
                "nodes": [
                    {"id": "gid://shopify/FulfillmentOrder/1", "status": "OPEN"},
                    {"id": "gid://shopify/FulfillmentOrder/2", "status": "CLOSED"},
                ]
            }
        }
    }
    created = {
        "fulfillmentCreate": {
            "fulfillment": {"id": "gid://shopify/Fulfillment/77"},
            "userErrors": [],
        }
    }
    fake = _Shopify({"PcdOrderFOs": fos, "fulfillmentCreate(": created})
    with _client(fake):
        rows = gql.order_fulfillment_orders(
            "s.myshopify.com", "tok", S, order_id="1001"
        )
        fid = gql.fulfillment_create_for_orders(
            "s.myshopify.com",
            "tok",
            S,
            fulfillment_order_ids=["1"],
            tracking={"number": "PC1", "url": "https://t"},
            notify_customer=True,
        )
    assert fake.requests[0]["variables"]["id"] == "gid://shopify/Order/1001"
    assert [r["status"] for r in rows] == ["OPEN", "CLOSED"]
    assert fid == "gid://shopify/Fulfillment/77"
    sent = fake.requests[1]["variables"]["fulfillment"]
    assert sent["lineItemsByFulfillmentOrder"] == [
        {"fulfillmentOrderId": "gid://shopify/FulfillmentOrder/1"}
    ]
    assert (
        sent["trackingInfo"]["company"] == "PorterChain"
        and sent["notifyCustomer"] is True
    )


def test_fulfillment_service_find_and_mark_paid() -> None:
    fs = {
        "shop": {
            "fulfillmentServices": [
                {
                    "id": "gid://shopify/FulfillmentService/5",
                    "serviceName": "Other",
                    "location": None,
                },
                {
                    "id": "gid://shopify/FulfillmentService/9",
                    "serviceName": "PorterChain",
                    "location": {"id": "gid://shopify/Location/3"},
                },
            ]
        }
    }
    paid = {
        "orderMarkAsPaid": {
            "order": {"id": "o", "transactions": [{"id": "t1"}, {"id": "t2"}]},
            "userErrors": [],
        }
    }
    with _client(_Shopify({"PcdFs": fs, "PcdPaid": paid})):
        assert gql.fulfillment_service_find("s", "tok", S) == (
            "gid://shopify/FulfillmentService/9",
            "gid://shopify/Location/3",
        )
        assert gql.order_mark_as_paid("s", "tok", S, order_id="1001") == "t2"


def test_no_rest_admin_calls_left() -> None:
    """Guard: the Shopify app talks to the Admin API only through GraphQL."""
    root = pathlib.Path(__file__).resolve().parents[1] / "src" / "porterchain_api"
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "/admin/api/" in text and "graphql.json" not in text:
            offenders.append(str(path))
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in {
                "_admin_get",
                "_admin_post",
            }:
                offenders.append(f"{path}:{node.lineno}")
            if isinstance(node, ast.FunctionDef) and node.name in {
                "_admin_get",
                "_admin_post",
            }:
                offenders.append(f"{path}:{node.lineno}")
    assert offenders == []


@pytest.mark.parametrize("status", [401, 403])
def test_graphql_http_errors_surface(status: int) -> None:
    fake = MagicMock()
    fake.__enter__ = lambda s: s
    fake.__exit__ = lambda *a: False
    fake.post.return_value = _resp({}, status)
    with _client(fake), pytest.raises(gql.ShopifyAdminError, match=f"http_{status}"):
        gql.shop_details("s", "tok", S)
