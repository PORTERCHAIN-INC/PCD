"""Shopify App Store review 139170: order sync ledger, reconcile, Billing API gate."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine import shopify_billing, shopify_order_sync, shopify_webhooks
from porterchain_api.merchant_models import Merchant, ShopifyOrderSync, ShopifyShop


def _settings_with(**kw) -> Settings:
    base = dict(_env_file=None, app_env="local", stripe_mock=True,
                jwt_secret="test-jwt-secret-key-32chars!!", shopify_api_key="pub139170", shopify_api_secret="shpss_139170",
                fleetbase_dispatch_bridge=False)
    base.update(kw)
    return Settings(**base)


def _settings() -> Settings:
    """Zero-arg so FastAPI dependency_overrides can use it."""
    return _settings_with()


@pytest.fixture
def shop(db: Session) -> ShopifyShop:
    sfx = uuid4().hex[:8]
    m = Merchant(status=MerchantStatus.ACTIVE.value, company_name=f"Vell {sfx}",
                 email=f"v-{sfx}@test.invalid", payment_terms="NET_30", profile={})
    db.add(m)
    db.flush()
    row = ShopifyShop(merchant_id=m.id, shop_domain=f"vell-{sfx}.myshopify.com",
                      scopes="read_orders", installed_at=datetime.now(UTC),
                      encrypted_access_token="enc", token_status="expiring")
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _order(oid=1374, title="Standard"):
    return {"id": oid, "name": f"#{oid}", "test": True, "financial_status": "paid",
            "currency": "CAD", "total_price": "36.05", "subtotal_price": "30.00",
            "created_at": "2026-11-03T10:00:00-05:00",
            "shipping_lines": [{"title": title, "code": title, "price": "6.05"}],
            "shipping_address": {"first_name": "A", "last_name": "B", "address1": "290 Bremner Blvd",
                                 "city": "Toronto", "province_code": "ON", "zip": "M5V 2T6",
                                 "country_code": "CA"},
            "line_items": [{"title": "Ring", "quantity": 1, "price": "30.00"}]}


def test_non_porterchain_rate_order_is_recorded_and_searchable(db: Session, shop: ShopifyShop):
    s = _settings()
    with patch.object(shopify_webhooks, "_book_from_shopify_payload",
                      return_value={"ok": True, "skipped": "not_porterchain_rate"}):
        shopify_webhooks.process_order_payload(db, s, shop_domain=shop.shop_domain,
                                               action="shopify_orders_create", body=_order())
    rows = shopify_order_sync.list_for_merchant(db, shop.merchant_id, q="#1374")
    assert len(rows) == 1
    r = rows[0]
    assert r["status"] == "not_booked" and r["reason_code"] == "not_porterchain_rate"
    assert r["can_book"] and r["total_cents"] == 3605 and r["is_test"]
    assert "Bremner" in (r["ship_to"] or "") and r["line_items"][0]["title"] == "Ring"
    assert shopify_order_sync.list_for_merchant(db, shop.merchant_id, q="1374")


def test_booked_then_cancel_then_delete_keeps_details(db: Session, shop: ShopifyShop):
    s = _settings()
    with patch.object(shopify_webhooks, "_book_from_shopify_payload",
                      return_value={"ok": True, "order_id": "ord-1"}):
        shopify_webhooks.process_order_payload(db, s, shop_domain=shop.shop_domain,
                                               action="shopify_orders_create", body=_order(1375))
    with patch.object(shopify_webhooks, "_update_from_shopify_payload",
                      return_value={"ok": True, "skipped": "no_change"}):
        shopify_webhooks.process_order_payload(db, s, shop_domain=shop.shop_domain,
                                               action="shopify_orders_updated", body=_order(1375))
    row = db.query(ShopifyOrderSync).filter_by(shop_domain=shop.shop_domain).one()
    assert row.status == "booked" and row.porterchain_order_id == "ord-1"
    with patch.object(shopify_webhooks, "_cancel_from_shopify_payload",
                      return_value={"ok": True, "order_id": "ord-1", "cancelled": True}):
        shopify_webhooks.process_order_payload(db, s, shop_domain=shop.shop_domain,
                                               action="shopify_orders_cancelled", body={"id": 1375},
                                               topic="orders/delete")
    db.refresh(row)
    assert row.status == "cancelled" and row.ship_to and row.order_name == "#1375"


def test_refund_payload_does_not_create_ledger_row(db: Session, shop: ShopifyShop):
    with patch.object(shopify_webhooks, "_cancel_from_shopify_payload", return_value={"ok": True}):
        shopify_webhooks.process_order_payload(_s := db, _settings(), shop_domain=shop.shop_domain,
                                               action="shopify_orders_cancelled",
                                               body={"id": 999, "order_id": 1374}, topic="refunds/create")
    assert db.query(ShopifyOrderSync).filter_by(shop_domain=shop.shop_domain).count() == 0


def test_error_is_recorded_and_reraised(db: Session, shop: ShopifyShop):
    with patch.object(shopify_webhooks, "_book_from_shopify_payload", side_effect=RuntimeError("boom")):
        with pytest.raises(RuntimeError):
            shopify_webhooks.process_order_payload(db, _settings(), shop_domain=shop.shop_domain,
                                                   action="shopify_orders_create", body=_order(1376))
    row = db.query(ShopifyOrderSync).filter_by(shop_domain=shop.shop_domain).one()
    assert row.status == "error" and row.can_book if hasattr(row, "can_book") else row.status == "error"


def test_reconcile_processes_only_unknown_orders(db: Session, shop: ShopifyShop):
    s = _settings()
    shopify_order_sync.record(db, shop, _order(1), action="shopify_orders_create",
                              result={"ok": True, "order_id": "x"})
    calls = []
    with patch.object(shopify_order_sync, "fetch_recent", return_value=[_order(1), _order(2)]), \
         patch.object(shopify_webhooks, "process_order_payload",
                      side_effect=lambda *a, **k: calls.append(k["body"]["id"]) or {"ok": True}):
        out = shopify_order_sync.reconcile_shop(db, s, shop)
    assert calls == [2] and out["new"] == 1


# --- Billing ---------------------------------------------------------------

def test_billing_gate_blocks_until_approved_and_after_decline(db: Session, shop: ShopifyShop):
    s = _settings()
    assert shopify_billing.booking_block(db, s, shop.merchant_id) == shopify_billing.BLOCK_CODE
    shop.billing_status = "active"
    db.commit()
    assert shopify_billing.booking_block(db, s, shop.merchant_id) is None
    shop.billing_status = "declined"
    db.commit()
    assert shopify_billing.booking_block(db, s, shop.merchant_id) == shopify_billing.BLOCK_CODE


def test_custom_app_and_direct_merchants_not_billed(db: Session, shop: ShopifyShop):
    s = _settings()
    shop.token_status = "custom_app"
    db.commit()
    assert not shopify_billing.is_shopify_billed(db, s, shop.merchant_id)
    assert shopify_billing.booking_block(db, s, shop.merchant_id) is None


def test_uninstall_resets_so_reinstall_asks_again(db: Session, shop: ShopifyShop):
    shop.billing_status = "active"
    shop.billing_subscription_gid = "gid://shopify/AppSubscription/1"
    shopify_billing.on_uninstall(shop)
    assert shop.billing_status is None and shop.billing_subscription_gid is None


def test_request_approval_is_capped_usage_and_test(db: Session, shop: ShopifyShop):
    s = _settings()
    seen = {}

    def fake(shop_, settings_, query, variables=None):
        if "shopBillingPreferences" in query:
            return {"shopBillingPreferences": {"currency": "CAD"}}
        seen.update(variables or {})
        return {"appSubscriptionCreate": {"userErrors": [], "confirmationUrl": "https://x/confirm",
                                          "appSubscription": {"id": "gid://shopify/AppSubscription/9",
                                                              "lineItems": [{"id": "gid://li/1"}]}}}

    with patch.object(shopify_billing, "_gql", side_effect=fake):
        url = shopify_billing.request_approval(db, s, shop)
    assert url == "https://x/confirm" and seen["test"] is True
    usage = seen["lineItems"][0]["plan"]["appUsagePricingDetails"]
    assert usage["cappedAmount"]["amount"] == pytest.approx(5000.0)


def test_status_refresh_maps_active_and_declined(db: Session, shop: ShopifyShop):
    s = _settings()
    shop.billing_subscription_gid = "gid://shopify/AppSubscription/9"
    db.commit()
    with patch.object(shopify_billing, "_gql", return_value={"currentAppInstallation": {
            "activeSubscriptions": [{"id": "gid://shopify/AppSubscription/9", "status": "ACTIVE",
                                     "test": True, "lineItems": [{"id": "gid://li/1"}]}]}}):
        assert shopify_billing.refresh_status(db, s, shop) == "active"
    with patch.object(shopify_billing, "_gql", return_value={"currentAppInstallation": {"activeSubscriptions": []}}):
        assert shopify_billing.refresh_status(db, s, shop) in {"declined", "cancelled"}


def test_book_path_skips_when_billing_not_approved(db: Session, shop: ShopifyShop):
    from porterchain_api.merchant_engine import shopify_payload_ops as ops

    body = _order(1400, "PorterChain Delivery")
    body["_force_book"] = True
    with patch.object(ops, "unpaid_non_cod", return_value=False):
        out = ops._book_from_shopify_payload(db, _settings(), shop_domain=shop.shop_domain, payload=body)
    assert out.get("skipped") == "shopify_billing_not_approved"


def test_order_query_needs_no_customer_scope_and_drops_weight_on_access_denied():
    from unittest.mock import patch as _p

    from porterchain_api.merchant_engine import shopify_order_sync as o
    from porterchain_api.merchant_engine.shopify_admin_graphql import ShopifyAdminError

    assert "customer {" not in o._ORDERS_Q
    calls = []

    def fake(_d, _t, _s, query, _v):
        calls.append(query)
        if "inventoryItem" in query:
            raise ShopifyAdminError("graphql_errors:ACCESS_DENIED")
        return {"ok": 1}

    with _p("porterchain_api.merchant_engine.shopify_admin_graphql.admin_graphql", side_effect=fake):
        assert o._gql("x.myshopify.com", "t", _settings(), o._ORDER_TMPL, {}) == {"ok": 1}
    assert len(calls) == 2 and "inventoryItem" not in calls[1]


def test_embedded_orders_need_a_valid_session_token(db: Session):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from porterchain_api.config import get_settings
    from porterchain_api.db import get_db
    from porterchain_api.routers import shopify as shopify_router

    app = FastAPI()
    app.include_router(shopify_router.router)
    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_db] = lambda: db
    c = TestClient(app)
    assert c.get("/v1/integrations/shopify/orders").status_code == 401
    assert c.get("/v1/integrations/shopify/orders", headers={"Authorization": "Bearer a.b.c"}).status_code == 401


# ---- round 2 (Nov 4): currency, plan change, cap, privacy of the order ledger, scopes ----

def test_usd_billed_store_is_charged_converted_amount(db: Session, shop: ShopifyShop):
    shopify_billing._fx_cache.clear()
    with patch.object(shopify_billing, "cad_per_unit", side_effect=lambda c: 1.0 if c == "CAD" else 1.40):
        assert shopify_billing.to_billing_currency(14.0, "USD") == pytest.approx(10.0)
        assert shopify_billing.to_billing_currency(9.0, "CAD") == pytest.approx(9.0)
    seen = {}

    def fake(shop_, settings_, query, variables=None):
        if "shopBillingPreferences" in query:
            return {"shopBillingPreferences": {"currency": "USD"}}
        seen.update(variables or {})
        return {"appSubscriptionCreate": {"userErrors": [], "confirmationUrl": "https://x/c",
                                          "appSubscription": {"id": "gid://shopify/AppSubscription/7"}}}

    with patch.object(shopify_billing, "_gql", side_effect=fake), \
         patch.object(shopify_billing, "cad_per_unit", return_value=1.25):
        shopify_billing.request_approval(db, _settings(), shop)
    cap = seen["lineItems"][0]["plan"]["appUsagePricingDetails"]["cappedAmount"]
    assert cap == {"amount": pytest.approx(4000.0), "currencyCode": "USD"}


def test_unknown_billing_currency_never_guesses(db: Session, shop: ShopifyShop):
    with patch.object(shopify_billing, "_gql", return_value={"shopBillingPreferences": {}}):
        with pytest.raises(RuntimeError):
            shopify_billing._billing_currency(shop, _settings())


def test_fx_fallback_when_bank_feed_down():
    shopify_billing._fx_cache.clear()
    import httpx
    with patch.object(httpx, "get", side_effect=OSError("down")):
        assert shopify_billing.cad_per_unit("USD") == pytest.approx(1.40)
        assert shopify_billing.cad_per_unit("CAD") == 1.0
    shopify_billing._fx_cache.clear()


def test_cap_reached_blocks_with_its_own_message(db: Session, shop: ShopifyShop):
    s = _settings()
    data = {"currentAppInstallation": {"activeSubscriptions": [{
        "id": "gid://shopify/AppSubscription/9", "status": "ACTIVE", "test": True,
        "lineItems": [{"id": "gid://li/1", "plan": {"pricingDetails": {
            "__typename": "AppUsagePricing", "cappedAmount": {"amount": "100", "currencyCode": "CAD"},
            "balanceUsed": {"amount": "100", "currencyCode": "CAD"}}}}]}]}}
    with patch.object(shopify_billing, "_gql", return_value=data):
        assert shopify_billing.refresh_status(db, s, shop) == "cap_reached"
    code = shopify_billing.booking_block(db, s, shop.merchant_id)
    assert code == shopify_billing.CAP_CODE
    assert "limit" in shopify_billing.block_message(code)


def test_merchant_can_change_cap_without_support(db: Session, shop: ShopifyShop):
    s = _settings()
    active = {"currentAppInstallation": {"activeSubscriptions": [{
        "id": "gid://shopify/AppSubscription/9", "status": "ACTIVE", "test": True,
        "lineItems": [{"id": "gid://li/1", "plan": {"pricingDetails": {
            "__typename": "AppUsagePricing", "cappedAmount": {"amount": "500", "currencyCode": "CAD"},
            "balanceUsed": {"amount": "10", "currencyCode": "CAD"}}}}]}]}}
    seen = {}

    def fake(shop_, settings_, query, variables=None):
        if "currentAppInstallation" in query:
            return active
        if "shopBillingPreferences" in query:
            return {"shopBillingPreferences": {"currency": "CAD"}}
        seen.update(variables or {})
        return {"appSubscriptionLineItemUpdate": {"userErrors": [], "confirmationUrl": "https://x/cap"}}

    with patch.object(shopify_billing, "_gql", side_effect=fake):
        assert shopify_billing.change_cap(db, s, shop, 2500) == "https://x/cap"
        with pytest.raises(ValueError):
            shopify_billing.change_cap(db, s, shop, 123)
    assert seen["id"] == "gid://li/1" and seen["cap"]["amount"] == pytest.approx(2500.0)


def test_approaching_cap_topic_refreshes_billing():
    import inspect
    src = inspect.getsource(shopify_webhooks)
    assert "app/subscriptions/approaching/capped/amount" in src


def test_customer_and_shop_redact_cover_order_ledger(db: Session, shop: ShopifyShop):
    from datetime import timedelta
    from porterchain_api.merchant_engine import shopify_privacy
    from porterchain_api.merchant_models import ShopifyDataSubjectRequest

    s = _settings()
    with patch.object(shopify_webhooks, "_book_from_shopify_payload",
                      return_value={"ok": True, "skipped": "not_porterchain_rate"}):
        for oid in (1501, 1502):
            shopify_webhooks.process_order_payload(db, s, shop_domain=shop.shop_domain,
                                                   action="shopify_orders_create", body=_order(oid))
    req = ShopifyDataSubjectRequest(shop_id=shop.id, merchant_id=shop.merchant_id, topic="customers/redact",
                                    shopify_webhook_id=uuid4().hex, orders_requested=["1501"],
                                    due_at=datetime.now(UTC) + timedelta(days=30))
    db.add(req)
    db.commit()
    shopify_privacy.process_privacy_request(db, s, req.id)
    rows = {r.shopify_order_id: r for r in db.query(ShopifyOrderSync).filter_by(shop_domain=shop.shop_domain)}
    assert rows["1501"].ship_to is None and rows["1501"].customer_name is None
    assert rows["1502"].ship_to
    req2 = ShopifyDataSubjectRequest(shop_id=shop.id, merchant_id=shop.merchant_id, topic="shop/redact",
                                     shopify_webhook_id=uuid4().hex,
                                     due_at=datetime.now(UTC) + timedelta(days=30))
    db.add(req2)
    db.commit()
    shopify_privacy.process_privacy_request(db, s, req2.id)
    assert db.query(ShopifyOrderSync).filter_by(shop_domain=shop.shop_domain).count() == 0


def test_released_scopes_are_minimal():
    from porterchain_api.merchant_engine.shopify_urls import _RELEASED_APP_SCOPES

    assert not any("assigned_fulfillment" in x for x in _RELEASED_APP_SCOPES)
