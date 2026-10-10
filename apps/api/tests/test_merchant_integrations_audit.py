"""Regression tests for the merchant Connections (Integrations) tab audit."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.merchant360_board import api_keys_payload
from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_engine.shopify_control_service import replay_ingress_dlq
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.merchant_models import (
    Merchant,
    MerchantApiKey,
    MerchantAuditLog,
    ShopifyIngressDlq,
    ShopifyShop,
)


def _ctx(role: str) -> AdminContext:
    return AdminContext(
        user=AdminUser(clerk_user_id=f"int-{role}", email=f"{role}@porterchain.com", role=role),
        role=parse_admin_role(role),
    )


@pytest.fixture
def merchant(db):
    row = Merchant(company_name=f"Int Co {uuid4().hex[:6]}", email="int@example.com", status="ACTIVE")
    db.add(row)
    db.commit()
    yield row


def _key(db, merchant_id: str, **kw) -> MerchantApiKey:
    raw = "pk_production_" + uuid4().hex
    k = MerchantApiKey(merchant_id=merchant_id, name="ERP", key_prefix=raw[:12],
                       key_hash=hashlib.sha256(raw.encode()).hexdigest(), environment="production", **kw)
    db.add(k)
    db.commit()
    return k


def test_integration_log_not_crowded_out_by_other_audit_rows(db, merchant):
    old = datetime.now(UTC) - timedelta(days=2)
    db.add(MerchantAuditLog(merchant_id=merchant.id, actor_user_id="admin:x", action="api_key.revoked",
                            resource_type="api_key", resource_id="k1", payload={}, created_at=old))
    for _ in range(60):
        db.add(MerchantAuditLog(merchant_id=merchant.id, actor_user_id="admin:x", action="pricing.updated",
                                resource_type="pricing", resource_id=None, payload={}))
    db.commit()
    events = api_keys_payload(db, merchant.id)["audit_events"]
    assert [e["action"] for e in events] == ["api_key.revoked"]


def test_rotated_key_past_grace_shows_inactive(db, merchant):
    _key(db, merchant.id, expires_at=datetime.now(UTC) - timedelta(minutes=5))
    live = _key(db, merchant.id)
    out = api_keys_payload(db, merchant.id)
    by_id = {k["id"]: k for k in out["api_keys"]}
    assert by_id[live.id]["is_active"] is True
    assert sum(1 for k in out["api_keys"] if k["is_active"]) == 1
    assert out["active_keys"] == 1


def test_tracking_sync_is_not_hardcoded(db, merchant):
    assert api_keys_payload(db, merchant.id)["shopify_partner"]["mid_flight_tracking"] is False


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)
    app.dependency_overrides[get_admin_context] = lambda: _ctx("admin")
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_rate_limit_out_of_range_is_rejected_not_clamped(client, db, merchant):
    k = _key(db, merchant.id, rate_limit_per_minute=60)
    r = client.patch(f"/v1/admin/merchants/{merchant.id}/api-keys/{k.id}/rate-limit",
                     json={"rate_limit_per_minute": 5000})
    assert r.status_code == 400
    db.refresh(k)
    assert k.rate_limit_per_minute == 60


def test_rate_limit_change_is_audited(client, db, merchant):
    k = _key(db, merchant.id, rate_limit_per_minute=60)
    r = client.patch(f"/v1/admin/merchants/{merchant.id}/api-keys/{k.id}/rate-limit",
                     json={"rate_limit_per_minute": 120})
    assert r.status_code == 200, r.text
    row = db.query(MerchantAuditLog).filter_by(merchant_id=merchant.id, action="api_key.rate_limit_changed").one()
    assert row.payload["rate_limit_per_minute"] == 120


def test_failed_dlq_replay_stays_open_with_reason(db, merchant, monkeypatch):
    shop = ShopifyShop(merchant_id=merchant.id, shop_domain=f"s{uuid4().hex[:6]}.myshopify.com",
                       encrypted_access_token="x")
    db.add(shop)
    db.commit()
    row = ShopifyIngressDlq(merchant_id=merchant.id, shop_id=shop.id, shop_domain=shop.shop_domain,
                            action="shopify_orders_create", reason_code="unknown", raw_body="{}", status="open")
    db.add(row)
    db.commit()

    def boom(*a, **k):
        raise ValueError("default_pickup_required")

    monkeypatch.setattr("porterchain_api.merchant_engine.shopify_service.process_queued_webhook", boom)
    out = replay_ingress_dlq(db, _ctx("admin"), merchant.id, row.id, get_settings())
    assert out["ok"] is False and out["replayed"] is False
    fresh = db.get(ShopifyIngressDlq, row.id)
    assert fresh.status == "open"
    assert fresh.attempts == 1
    assert fresh.reason_code != "unknown"
