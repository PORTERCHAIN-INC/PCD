"""Shopify end to end on a real DB with Shopify stubbed at the HTTP boundary.

install/OAuth → checkout rate → orders/create → booking → fulfillment + tracking
sync → return → uninstall → GDPR, and at each step the merchant view, the
admin view and the watchdog must agree on the store's status.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from contextlib import ExitStack
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from porterchain_api.admin_engine.merchant360_board import api_keys_payload
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_engine.shopify_control_service import set_ingress_paused
from porterchain_api.admin_models import AdminUser
from porterchain_api.booking_models import Order
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine import shopify_service as shopify
from porterchain_api.merchant_engine.account_ops.connections import watchdog
from porterchain_api.merchant_engine.shopify_one_click import connection_payload
from porterchain_api.merchant_models import (
    Merchant,
    MerchantUser,
    SavedAddress,
    ShopifyIngressDlq,
    ShopifyShop,
)

_GQL = "porterchain_api.merchant_engine.shopify_admin_graphql"
FULL_SCOPES = (
    "read_assigned_fulfillment_orders,read_merchant_managed_fulfillment_orders,read_orders,"
    "write_assigned_fulfillment_orders,write_fulfillments,write_merchant_managed_fulfillment_orders,"
    "write_shipping"
)


def _settings() -> Settings:
    return Settings(
        _env_file=None,
        app_env="local",
        stripe_mock=True,
        jwt_secret="test-jwt-secret-key-32chars!!",
        porterchain_api_url="https://api.porterchain.com",
        merchant_portal_url="https://merchant.porterchain.com",
        shopify_api_key="cid",
        shopify_api_secret="shpss_test",
        fleetbase_dispatch_bridge=False,
        spicedb_enabled=False,
        spicedb_use_memory=True,
        spicedb_required=False,
    )


def _sig(body: bytes) -> str:
    return base64.b64encode(hmac.new(b"shpss_test", body, hashlib.sha256).digest()).decode()


def _admin(role: str) -> AdminContext:
    return AdminContext(
        user=AdminUser(clerk_user_id=f"e2e-{role}", email=f"{role}@porterchain.com", role=role),
        role=parse_admin_role(role),
    )


def _views(db, settings, merchant_id: str, shop_id: str) -> dict[str, dict]:
    with patch("porterchain_api.admin_engine.merchant360_board.get_settings", return_value=settings, create=True):
        admin = next(s for s in api_keys_payload(db, merchant_id)["shopify_shops"] if s["id"] == shop_id)
    merchant = next(s for s in connection_payload(db, merchant_id, settings)["shops"] if s["id"] == shop_id)
    watch = next(i for i in watchdog(db, merchant_id, settings)["items"] if i["id"] == shop_id)
    return {"merchant": merchant["health"], "admin": admin["health"], "watchdog": watch["health"]}


def _agree(db, settings, merchant_id, shop_id) -> dict:
    v = _views(db, settings, merchant_id, shop_id)
    keys = ("state", "light", "reason", "fix", "orders_waiting")
    assert {k: v["merchant"][k] for k in keys} == {k: v["admin"][k] for k in keys} == {
        k: v["watchdog"][k] for k in keys
    }, v
    return v["merchant"]


@pytest.fixture
def company(db):
    suffix = uuid4().hex[:8]
    m = Merchant(company_name=f"E2E {suffix}", email=f"e2e-{suffix}@test.local", status=MerchantStatus.ACTIVE.value,
                 payment_terms="NET_30", profile={})
    db.add(m)
    db.flush()
    db.add(MerchantUser(merchant_id=m.id, clerk_user_id=f"user_{suffix}", email=f"o-{suffix}@test.local",
                        role=MerchantRole.OWNER.value, is_active=True))
    db.add(SavedAddress(merchant_id=m.id, label="Warehouse", address_type="pickup", is_default=True,
                        formatted="1 King St W, Toronto, ON M5H 1A1", postal="M5H1A1", lat=43.6487, lng=-79.3774))
    db.commit()
    return m


def _stub_shopify(stack: ExitStack) -> dict[str, MagicMock]:
    """Every outbound Shopify call is a stub; nothing leaves the machine."""
    calls = {
        "exchange": stack.enter_context(patch.object(
            shopify, "_exchange_token", return_value={"access_token": "tok", "scope": FULL_SCOPES})),
        "get": stack.enter_context(patch.object(
            shopify, "_admin_get", side_effect=lambda shop, tok, path, *a, **k: (
                {"shop": {"id": 42, "email": "owner@shop.test"}} if path.startswith("/shop")
                else {"fulfillment_orders": [{"id": 9001}]}))),
        "post": stack.enter_context(patch.object(
            shopify, "_admin_post", return_value={"fulfillment": {"id": 7001}})),
        "gql": stack.enter_context(patch(f"{_GQL}.admin_graphql", return_value={})),
        "hooks": stack.enter_context(patch("porterchain_api.merchant_engine.shopify_fulfillment_service._register_webhooks")),
        "carrier": stack.enter_context(patch(f"{_GQL}.carrier_service_create", return_value="gid://shopify/DeliveryCarrierService/1")),
        "carrier_upd": stack.enter_context(patch(f"{_GQL}.carrier_service_update", return_value="gid://shopify/DeliveryCarrierService/1")),
        "event": stack.enter_context(patch(f"{_GQL}.fulfillment_event_create", return_value={})),
        "tracking": stack.enter_context(patch(f"{_GQL}.fulfillment_tracking_update", return_value={})),
        "verify": stack.enter_context(patch.object(shopify, "verify_oauth_hmac", return_value=True)),
        "geo": stack.enter_context(patch.object(shopify, "_ensure_coords", side_effect=lambda a: a)),
        "publish": stack.enter_context(patch("porterchain_shared.queue.publisher.get_queue_publisher")),
    }
    stack.enter_context(patch("porterchain_api.integrations.shopify_carrier_rates._ensure_geo", side_effect=lambda a: a))
    return calls


def _order_payload(order_id: int) -> dict:
    return {
        "id": order_id,
        "name": f"#{order_id}",
        "financial_status": "paid",
        "shipping_lines": [{"code": "porterchain_same_day", "source": "PorterChain", "title": "PorterChain"}],
        "shipping_address": {"address1": "200 Bay St", "city": "Toronto", "province_code": "ON", "zip": "M5J2J5",
                             "country_code": "CA", "latitude": 43.6466, "longitude": -79.3789, "name": "Buyer"},
        "line_items": [{"grams": 1000, "quantity": 1, "title": "Box"}],
    }


def _queue(db, settings, shop_domain: str, topic: str, body: dict, calls) -> dict:
    """Webhook in → (stubbed) queue → worker, exactly like production but in-process."""
    raw = json.dumps(body).encode()
    enqueue = calls["publish"].return_value.enqueue
    enqueue.reset_mock()
    out = shopify.ingest_webhook(db, settings, raw_body=raw, hmac_header=_sig(raw), shop_domain_header=shop_domain,
                                 topic=topic, webhook_id=uuid4().hex)
    if not out.get("queued"):
        return out
    return shopify.process_queued_webhook(db, settings, enqueue.call_args.args[1])


def test_install_rate_order_fulfil_track_return_uninstall_redact(db, company):
    from porterchain_api.integrations.shopify_carrier_rates import carrier_service_rates
    from porterchain_api.merchant_engine.shopify_fulfillment_ops import push_fulfillment
    from porterchain_api.merchant_engine.shopify_privacy import (
        open_privacy_request,
        process_privacy_request,
    )

    settings = _settings()
    domain = f"e2e-{uuid4().hex[:8]}.myshopify.com"
    with ExitStack() as stack:
        calls = _stub_shopify(stack)

        # 1. install / OAuth links the store to the signed-in company (existing account)
        shop = shopify.complete_oauth(db, settings, shop_domain=domain, code="c",
                                      state=shopify.sign_oauth_state(company.id, settings), query_string="x")
        assert shop.merchant_id == company.id and shop.carrier_service_gid
        assert shop.scopes == FULL_SCOPES
        st = _agree(db, settings, company.id, shop.id)
        assert st["state"] == "connected" and st["missing_scopes"] == []

        # 2. checkout rate (real pricing engine, geo stubbed)
        rate_body = {"rate": {"currency": "CAD",
                              "origin": {"postal_code": "M5H1A1", "country": "CA", "province": "ON"},
                              "destination": {"postal_code": "M5J2J5", "country": "CA", "province": "ON",
                                              "city": "Toronto", "address1": "200 Bay St"},
                              "items": [{"name": "Box", "quantity": 1, "grams": 1000}]}}
        raw = json.dumps(rate_body).encode()
        rates = carrier_service_rates(db, settings, raw_body=raw, hmac_header=_sig(raw), shop_domain=domain,
                                      payload=rate_body)
        assert rates["rates"], rates
        assert all(int(r["total_price"]) > 0 for r in rates["rates"])

        # 3. paused store: order is held, every view says paused, resume books it
        set_ingress_paused(db, _admin("super_admin"), company.id, shop.id, paused=True, reason="audit", settings=settings)
        held = _queue(db, settings, domain, "orders/create", _order_payload(1001), calls)
        assert held.get("held") is True
        st = _agree(db, settings, company.id, shop.id)
        assert st["state"] == "paused" and st["fix"] == "resume_orders" and st["orders_waiting"] == 1
        assert "orders_paused" in connection_payload(db, company.id, settings)["go_live"]["blocking"]
        resumed = set_ingress_paused(db, _admin("super_admin"), company.id, shop.id, paused=False, reason="ok",
                                     settings=settings)
        assert resumed["released"] == 1, resumed
        assert _agree(db, settings, company.id, shop.id)["orders_waiting"] == 0

        # 4. live order → booking, held for ops while auto-dispatch is off
        booked = _queue(db, settings, domain, "orders/create", _order_payload(1002), calls)
        assert booked["order_id"] and booked["held_for_ops"] is True
        order = db.get(Order, booked["order_id"])

        # 5. fulfillment + tracking sync back to Shopify
        order.state = "PICKED_UP"
        db.commit()
        push_fulfillment(db, settings, order, event_type="picked_up")
        meta = (db.get(Order, order.id).compliance_metadata or {})["shopify"]
        assert meta["fulfillment_id"] == "7001", meta
        assert meta["last_tracking_push_at"] and "last_fulfillment_error" not in meta
        order.state = "IN_TRANSIT"
        db.commit()
        push_fulfillment(db, settings, order, event_type="in_transit")  # tracking update, not a 2nd fulfillment
        assert calls["post"].call_count == 1
        assert calls["tracking"].call_count == 1
        assert calls["event"].call_count == 2  # picked up, in transit
        with patch("porterchain_api.admin_engine.merchant360_board.get_settings", return_value=settings, create=True):
            partner = api_keys_payload(db, company.id)["shopify_partner"]
        assert partner["mid_flight_tracking"] is bool(meta.get("last_tracking_push_at"))

        # 6. return approved in Shopify → return pickup booked
        ret = _queue(db, settings, domain, "returns/approve",
                     {"id": "ret-1", "order_id": 1002, "admin_graphql_api_id": "gid://shopify/Return/1"}, calls)
        assert ret.get("return") is True, ret

        # 7. GDPR: data_request + customers/redact acknowledged without buyer contact
        req = open_privacy_request(db, topic="customers/data_request", shop=shop,
                                   raw_body=json.dumps({"shop_domain": domain, "customer": {"id": 9},
                                                        "orders_requested": [1002]}).encode(),
                                   webhook_id=uuid4().hex)
        assert process_privacy_request(db, settings, req["request_id"])["status"] == "fulfilled"

        # 8. uninstall: disconnected everywhere, reconnect fix offered
        out = _queue(db, settings, domain, "app/uninstalled", {"id": 42, "domain": domain}, calls)
        assert out["uninstalled"] is True
        st = _agree(db, settings, company.id, shop.id)
        assert st["state"] == "disconnected" and st["fix"] == "reconnect"

        # 9. shop/redact after uninstall clears the token
        red = open_privacy_request(db, topic="shop/redact", shop=shop,
                                   raw_body=json.dumps({"shop_domain": domain}).encode(), webhook_id=uuid4().hex)
        process_privacy_request(db, settings, red["request_id"])

        # 10. reconnect by the same company is clean and green again
        again = shopify.complete_oauth(db, settings, shop_domain=domain, code="c2",
                                       state=shopify.sign_oauth_state(company.id, settings), query_string="x")
        assert again.id == shop.id and again.uninstalled_at is None
        assert _agree(db, settings, company.id, shop.id)["state"] == "connected"


def test_missing_scope_is_red_in_every_view(db, company):
    settings = _settings()
    shop = ShopifyShop(merchant_id=company.id, shop_domain=f"s-{uuid4().hex[:6]}.myshopify.com",
                       installed_at=datetime.now(UTC), encrypted_access_token="enc",
                       scopes="read_orders,write_shipping", carrier_service_gid="gid://x/1")
    db.add(shop)
    db.commit()
    st = _agree(db, settings, company.id, shop.id)
    assert st["light"] == "red" and st["fix"] == "reconnect" and "write_fulfillments" in st["missing_scopes"]
    assert "scopes_missing" in connection_payload(db, company.id, settings)["go_live"]["blocking"]


def test_write_grant_implies_read(db, company):
    from porterchain_api.merchant_engine.shopify_urls import has_returns_scope

    assert has_returns_scope("write_returns") is True


def test_token_without_uninstall_is_disconnected_in_admin_too(db, company):
    settings = _settings()
    shop = ShopifyShop(merchant_id=company.id, shop_domain=f"t-{uuid4().hex[:6]}.myshopify.com",
                       installed_at=datetime.now(UTC), encrypted_access_token=None, scopes=FULL_SCOPES)
    db.add(shop)
    db.commit()
    st = _agree(db, settings, company.id, shop.id)
    assert st["state"] == "disconnected"
    with patch("porterchain_api.admin_engine.merchant360_board.get_settings", return_value=settings, create=True):
        row = next(s for s in api_keys_payload(db, company.id)["shopify_shops"] if s["id"] == shop.id)
    assert row["installed"] is False


def test_paused_store_holds_returns_too(db, company):
    settings = _settings()
    shop = ShopifyShop(merchant_id=company.id, shop_domain=f"p-{uuid4().hex[:6]}.myshopify.com",
                       installed_at=datetime.now(UTC), encrypted_access_token="enc", scopes=FULL_SCOPES,
                       ingress_paused=True)
    db.add(shop)
    db.commit()
    out = shopify.process_queued_webhook(db, settings, {
        "action": "shopify_return_approve", "shop_domain": shop.shop_domain, "topic": "returns/approve",
        "raw_body": json.dumps({"id": "r1", "order_id": 5})})
    assert out.get("held") is True
    assert db.query(ShopifyIngressDlq).filter_by(shop_id=shop.id, status="held").count() == 1


def test_admin_rate_limit_module_rejects_out_of_range():
    from porterchain_api.merchant_engine.api_key_limits import validate_rate_limit

    for bad in (9, 601, "x", None):
        with pytest.raises(ValueError):
            validate_rate_limit(bad)
    assert validate_rate_limit("120") == 120


def test_tracking_failure_surfaces_in_every_view(db, company):
    settings = _settings()
    shop = ShopifyShop(merchant_id=company.id, shop_domain=f"k-{uuid4().hex[:6]}.myshopify.com",
                       installed_at=datetime.now(UTC), encrypted_access_token="enc", scopes=FULL_SCOPES,
                       carrier_service_gid="gid://x/1", last_webhook_at=datetime.now(UTC))
    db.add(shop)
    order = Order(order_number=f"PC-{uuid4().hex[:8]}", tracking_number=f"T{uuid4().hex[:8]}", state="PICKED_UP",
                  merchant_id=company.id, amount_cents=1000, currency="cad", order_source="SHOPIFY",
                  pickup={"formatted": "a"}, dropoff={"formatted": "b"}, scheduled_at=datetime.now(UTC),
                  compliance_metadata={"shopify": {"shop_domain": shop.shop_domain, "order_id": "1",
                                                   "last_fulfillment_error": "missing_access_token"}})
    db.add(order)
    db.commit()
    st = _agree(db, settings, company.id, shop.id)
    assert st["light"] == "red" and st["fix"] == "retry_tracking" and st["tracking_failing_orders"] == [order.id]


def test_merchant_self_disconnect_is_audited_once(db, company):
    from porterchain_api.merchant_engine.rbac import MerchantContext
    from porterchain_api.merchant_models import MerchantAuditLog

    shop = ShopifyShop(merchant_id=company.id, shop_domain=f"d-{uuid4().hex[:6]}.myshopify.com",
                       installed_at=datetime.now(UTC), encrypted_access_token="enc", scopes=FULL_SCOPES)
    db.add(shop)
    db.commit()
    owner = db.query(MerchantUser).filter_by(merchant_id=company.id).first()
    with patch.object(shopify, "_delete_partner_services"):
        shopify.disconnect_shop(db, MerchantContext(merchant=company, user=owner, role=MerchantRole.OWNER), shop.id)
    rows = db.query(MerchantAuditLog).filter_by(merchant_id=company.id, resource_id=shop.id).all()
    assert [r.action for r in rows] == ["shopify.disconnected"]
    with patch("porterchain_api.admin_engine.merchant360_board.get_settings", return_value=_settings(), create=True):
        assert "shopify.disconnected" in [e["action"] for e in api_keys_payload(db, company.id)["audit_events"]]


# Persona permission matrix (asserted, and copied into report.md).
ADMIN_MATRIX = {
    # role: (view connections, everyday actions, elevated actions)
    "super_admin": (True, True, True),
    "compliance": (True, True, True),
    "admin": (True, True, False),
    "sales": (True, True, False),
    "finance": (True, False, False),
    "support": (True, False, False),
    "dispatcher": (True, False, False),
}


@pytest.mark.parametrize("role,expected", ADMIN_MATRIX.items())
def test_admin_persona_permissions(role, expected):
    from porterchain_api.admin_engine.merchant_org import require_integrations_elevated

    # Admin module grants are SpiceDB tuples generated from MODULE_PERMISSIONS; check the source of truth.
    from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS

    ctx = _admin(role)
    view = ctx.role in MODULE_PERMISSIONS["merchants_read"]
    act = ctx.role in MODULE_PERMISSIONS["merchants"]
    try:
        require_integrations_elevated(ctx)
        elevated = True
    except PermissionError:
        elevated = False
    assert (view, act, elevated) == expected


def test_merchant_persona_permissions():
    from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS

    assert MODULE_PERMISSIONS["api_keys"] == frozenset({MerchantRole.OWNER, MerchantRole.ADMIN})


def test_merchant_key_list_marks_rotated_key_past_grace_inactive():
    from datetime import timedelta
    from types import SimpleNamespace

    from porterchain_api.routers.merchant._deps import _api_key_out

    base = dict(id="k", name="n", key_prefix="pk", scopes=[], environment="production",
                rate_limit_per_minute=60, is_active=True, created_at=datetime.now(UTC))
    old = _api_key_out(SimpleNamespace(**base, expires_at=datetime.now(UTC) - timedelta(hours=1)))
    grace = _api_key_out(SimpleNamespace(**base, expires_at=datetime.now(UTC) + timedelta(days=3)))
    assert old.is_active is False and grace.is_active is True and grace.expires_at
