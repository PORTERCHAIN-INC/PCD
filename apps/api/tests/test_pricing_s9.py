"""Doc 72 §9: send quote (72 h), per-order adjustments with limits, Shopify flat-rate fallback."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.integrations.shopify_carrier_rates import flat_rate_fallback
from porterchain_api.main import app
from porterchain_api.pricing_engine.models import PricingSentQuote
from tests.fk_parents import make_order

ITEM = {"weight_kg": 4, "length_cm": 40, "width_cm": 30, "height_cm": 20}


def _client(db, role):
    ctx = AdminContext(user=AdminUser(auth_subject=f"pc-{role}", email=f"{role}@porterchain.com", role=role),
                       role=parse_admin_role(role))
    app.dependency_overrides[get_admin_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_send_quote_valid_72h_then_expires(db):
    try:
        c = _client(db, "admin")
        with patch("porterchain_api.notification_engine.delivery_service.DeliveryService.deliver",
                   return_value=SimpleNamespace(status="queued")) as deliver:
            r = c.post("/v1/pricing/quotes/send", json={"items": [ITEM], "email": "buyer@shop.ca", "audience": "retail"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["total_cents"] == 2034 and body["delivery"]["sent"] and deliver.called
        exp = datetime.fromisoformat(body["expires_at"])
        assert timedelta(hours=71, minutes=59) < exp - datetime.now(UTC) <= timedelta(hours=72)
        pub = c.get(f"/v1/public/quotes/{body['token']}")
        assert pub.status_code == 200 and pub.json()["total_cents"] == 2034
        row = db.get(PricingSentQuote, body["id"])
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.flush()
        assert c.get(f"/v1/public/quotes/{body['token']}").status_code == 410
        assert c.post(f"/v1/public/quotes/{body['token']}/accept").status_code == 410
        r2 = c.post("/v1/pricing/quotes/send", json={"items": [ITEM], "email": "b@shop.ca"})
        assert c.post(f"/v1/public/quotes/{r2.json()['token']}/accept").json()["status"] == "accepted"
        assert c.post("/v1/pricing/quotes/send", json={"items": [{"weight_kg": 300}], "email": "b@shop.ca"}).status_code == 422
        assert _client(db, "dispatcher").post("/v1/pricing/quotes/send", json={"items": [ITEM], "email": "b@shop.ca"}).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_order_adjustment_limits(db):
    order = make_order(db)  # $50.00
    try:
        a = _client(db, "admin")
        url = f"/v1/pricing/orders/{order.id}/adjustments"
        assert a.get(url).json()["limit_cents"] == 1000  # 20 % of $50
        assert a.post(url, json={"cents": 1500, "category": "waiting", "reason": "45 min wait"}).json()["detail"].startswith("over_limit")
        assert a.post(url, json={"cents": 500, "category": "waiting", "reason": "x"}).json()["detail"] == "reason_required"
        assert a.post(url, json={"cents": 500, "category": "bogus", "reason": "long enough"}).status_code == 422
        r = a.post(url, json={"cents": 750, "category": "waiting", "reason": "30 min wait at dock"})
        assert r.status_code == 200 and r.json()["adjusted_total_cents"] == 5750
        s = _client(db, "super_admin")
        assert s.post(url, json={"cents": -2500, "category": "goodwill", "reason": "late delivery"}).json()["adjusted_total_cents"] == 3250
        assert _client(db, "dispatcher").get(url).status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_shopify_flat_rate_fallback(db):
    on = flat_rate_fallback(db, SimpleNamespace(shopify_flat_rate_fallback_cents=None))
    rate = on["rates"][0]
    assert rate["service_code"] == "porterchain_flat_rate" and rate["total_price"] == str((4900 + 3000) * 113 // 100)
    assert flat_rate_fallback(db, SimpleNamespace(shopify_flat_rate_fallback_cents=0)) is None
    assert flat_rate_fallback(db, SimpleNamespace(shopify_flat_rate_fallback_cents=3999))["rates"][0]["total_price"] == "3999"
