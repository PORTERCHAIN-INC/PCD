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
    found = next(k for k in listed.json()["api_keys"] if k["id"] == key_id)
    assert found["is_active"] is False
    assert "shopify_shops" in listed.json()


def test_admin_deactivate_webhook(client, merchant, db):
    from porterchain_api.merchant_models import MerchantWebhook

    row = MerchantWebhook(
        merchant_id=merchant.id,
        url="https://example.com/hooks/porterchain",
        events=["order.delivered"],
        secret_hash="deadbeef",
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
