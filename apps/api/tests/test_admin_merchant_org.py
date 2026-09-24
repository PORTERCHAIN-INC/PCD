"""Admin writes the same company file, people, and places as the merchant portal."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant


@pytest.fixture
def merchant(db):
    row = Merchant(
        company_name="Org File Co",
        email="org-file@example.com",
        status="ACTIVE",
    )
    db.add(row)
    db.commit()
    yield row


@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)
    monkeypatch.setattr(
        "porterchain_api.routers.merchants_integrations.require_module",
        lambda ctx, module: None,
    )
    admin = AdminContext(
        user=AdminUser(clerk_user_id="org-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_admin_address_and_recipient_round_trip(client, merchant):
    created = client.post(
        f"/v1/admin/merchants/{merchant.id}/addresses",
        json={
            "label": "HQ",
            "address_type": "pickup",
            "formatted": "100 King St W, Toronto",
            "postal": "M5X 1A1",
            "is_default": True,
        },
    )
    assert created.status_code == 201, created.text
    address_id = created.json()["id"]
    listed = client.get(f"/v1/admin/merchants/{merchant.id}/locations").json()
    assert listed["addresses"][0]["label"] == "HQ"
    assert listed["addresses"][0]["postal"] == "M5X 1A1"

    rec = client.post(
        f"/v1/admin/merchants/{merchant.id}/recipients",
        json={"name": "Jane Dock", "email": "jane@example.com"},
    )
    assert rec.status_code == 201, rec.text
    assert rec.json()["name"] == "Jane Dock"

    defaulted = client.post(f"/v1/admin/merchants/{merchant.id}/addresses/{address_id}/default")
    assert defaulted.status_code == 200
    assert defaulted.json()["is_default"] is True


def test_admin_contact_and_billing_contact_english_errors(client, merchant):
    created = client.post(
        f"/v1/admin/merchants/{merchant.id}/contacts",
        json={"first_name": "Avery", "email": "ap@example.com", "roles": ["accounts_payable"]},
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["can_delete"] is True
    assert body["source"] == "manual"

    rows = client.get(f"/v1/admin/merchants/{merchant.id}/contacts").json()
    assert any(row["email"] == "ap@example.com" for row in rows)

    bill = client.post(
        f"/v1/admin/merchants/{merchant.id}/billing-contacts",
        json={"name": "AP", "email": "ap@example.com"},
    )
    assert bill.status_code == 201, bill.text
    assert bill.json()["is_primary"] is True

    missing = client.patch(
        f"/v1/admin/merchants/{merchant.id}/addresses/missing-id",
        json={"label": "Nope"},
    )
    assert missing.status_code == 404
    assert "location" in missing.json()["detail"].lower()


def test_admin_revoke_api_key(client, merchant, db):
    from porterchain_api.merchant_models import MerchantApiKey

    row = MerchantApiKey(
        merchant_id=merchant.id,
        name="leak",
        key_prefix="pk_test_xxxx",
        key_hash="deadbeef",
        scopes=[],
        environment="sandbox",
        is_active=True,
    )
    db.add(row)
    db.commit()
    key_id = row.id

    revoked = client.delete(f"/v1/admin/merchants/{merchant.id}/api-keys/{key_id}")
    assert revoked.status_code == 204, revoked.text

    listed = client.get(f"/v1/admin/merchants/{merchant.id}/api")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    found = next(k for k in body["api_keys"] if k["id"] == key_id)
    assert found["is_active"] is False
    assert "shopify_shops" in body
    assert "usage" in body
    assert "rate_limits" in body
    assert "sandbox_mode" in body
    assert "recent_webhook_deliveries" in body
    assert body["shopify_connected"] is False
    assert "shopify_webhook_url" in body


def test_admin_deactivate_webhook(client, merchant, db):
    from porterchain_api.merchant_models import MerchantWebhook

    row = MerchantWebhook(
        merchant_id=merchant.id,
        url="https://example.com/hooks/porterchain",
        events=["order.delivered"],
        secret_hash="deadbeef",
        environment="sandbox",
        is_active=True,
    )
    db.add(row)
    db.commit()
    hook_id = row.id

    disabled = client.delete(f"/v1/admin/merchants/{merchant.id}/webhooks/{hook_id}")
    assert disabled.status_code == 204, disabled.text

    listed = client.get(f"/v1/admin/merchants/{merchant.id}/api")
    assert listed.status_code == 200, listed.text
    found = next(w for w in listed.json()["webhooks"] if w["id"] == hook_id)
    assert found["is_active"] is False
    assert found["environment"] == "sandbox"


def test_admin_reenable_webhook(client, merchant, db):
    from porterchain_api.merchant_models import MerchantWebhook

    row = MerchantWebhook(
        merchant_id=merchant.id,
        url="https://example.com/hooks/porterchain-reenable",
        events=["order.delivered"],
        secret_hash="deadbeef",
        environment="production",
        is_active=False,
    )
    db.add(row)
    db.commit()
    hook_id = row.id

    enabled = client.post(f"/v1/admin/merchants/{merchant.id}/webhooks/{hook_id}/enable")
    assert enabled.status_code == 204, enabled.text

    listed = client.get(f"/v1/admin/merchants/{merchant.id}/api")
    assert listed.status_code == 200, listed.text
    body = listed.json()
    found = next(w for w in body["webhooks"] if w["id"] == hook_id)
    assert found["is_active"] is True
    assert "audit_events" in body
    assert "shopify_partner" in body
    assert "carrier_rates_url" in body["shopify_partner"]


def test_admin_freeze_partner_api(client, merchant, db):
    from porterchain_api.merchant_models import MerchantApiKey, MerchantWebhook

    key = MerchantApiKey(
        merchant_id=merchant.id,
        name="live",
        key_prefix="pk_test_live",
        key_hash="cafebabe",
        scopes=[],
        environment="production",
        is_active=True,
    )
    hook = MerchantWebhook(
        merchant_id=merchant.id,
        url="https://example.com/hooks/freeze",
        events=["order.booked"],
        secret_hash="deadbeef",
        environment="production",
        is_active=True,
    )
    db.add(key)
    db.add(hook)
    db.commit()

    frozen = client.post(
        f"/v1/admin/merchants/{merchant.id}/integrations/freeze",
        json={"reason": "abuse investigation"},
    )
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["keys_revoked"] == 1
    assert frozen.json()["webhooks_disabled"] == 1

    listed = client.get(f"/v1/admin/merchants/{merchant.id}/api")
    body = listed.json()
    assert next(k for k in body["api_keys"] if k["id"] == key.id)["is_active"] is False
    assert next(w for w in body["webhooks"] if w["id"] == hook.id)["is_active"] is False
    actions = [e["action"] for e in body.get("audit_events") or []]
    assert "partner_api.frozen" in actions


def test_admin_apply_kaylulu_and_clone_pricing(client, merchant, db):
    from porterchain_api.merchant_models import Merchant

    source = Merchant(
        company_name="Kaylulu Source",
        email="kaylulu-source@example.com",
        status="ACTIVE",
        pricing_model="distance",
    )
    db.add(source)
    db.commit()

    applied = client.post(f"/v1/admin/merchants/{source.id}/pricing/apply-kaylulu")
    assert applied.status_code == 200, applied.text
    body = applied.json()
    assert body["pricing_model"] == "fsa"
    assert body["schedule"]["fsa_miss"] == "refuse"
    assert body["schedule"]["origin_pickup_cents"] == 4000
    assert len(body["size_tiers"]) == 4
    assert body["size_tiers"][1]["label"] == "Handling Tier 1"
    assert body["size_tiers"][1]["surcharge_cents"] == 3000

    cloned = client.post(f"/v1/admin/merchants/{merchant.id}/pricing/clone-from/{source.id}")
    assert cloned.status_code == 200, cloned.text
    cloned_body = cloned.json()
    assert cloned_body["pricing_model"] == "fsa"
    assert cloned_body["schedule"]["route_minimums_cents"]["T1"] == 12000
    assert len(cloned_body["size_tiers"]) == 4


def test_admin_ar_preview_on_merchant_file(client, merchant):
    previewed = client.get(f"/v1/admin/merchants/{merchant.id}/ar/preview")
    assert previewed.status_code == 200, previewed.text
    body = previewed.json()
    assert body["merchant_id"] == merchant.id
    assert "order_count" in body
    assert "uninvoiced_cents" in body

    generated = client.post(f"/v1/admin/merchants/{merchant.id}/ar/generate")
    assert generated.status_code == 200, generated.text
    assert generated.json()["created_count"] == 0
    assert generated.json()["skipped_count"] >= 0


def test_admin_stripe_column_and_cod_round_trip(client, merchant):
    patched = client.patch(
        f"/v1/admin/merchants/{merchant.id}",
        json={"stripe_enabled": True, "cod_enabled": True},
    )
    assert patched.status_code == 200, patched.text
    body = patched.json()
    assert body["stripe_enabled"] is True
    assert body["cod_enabled"] is True

    again = client.get(f"/v1/admin/merchants/{merchant.id}")
    assert again.status_code == 200, again.text
    detail = again.json()
    assert detail["stripe_enabled"] is True
    assert detail["cod_enabled"] is True
