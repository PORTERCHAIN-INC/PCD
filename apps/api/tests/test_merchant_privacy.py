"""Merchant privacy DSR persist, English audit, admin execute copy."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.compliance_engine.privacy_service import (
    PrivacyService,
    merchant_privacy_file,
)
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_engine.audit_copy import summarize_audit_action
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantUser
from porterchain_api.reporting.switching_costs import rbac_and_audit_snapshot


def _merchant_ctx(db):
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Privacy Co {suffix}",
        email=f"privacy-{suffix}@test.local",
        status=MerchantStatus.ACTIVE.value,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"clerk_{suffix}",
        email=f"user-{suffix}@test.local",
        role=MerchantRole.OWNER.value,
    )
    db.add(user)
    db.flush()
    return MerchantContext(merchant=merchant, user=user, role=MerchantRole.OWNER)


def test_summarize_audit_action_english():
    assert summarize_audit_action("privacy.delete_requested") == "Deletion requested"
    assert "invoice" in summarize_audit_action("invoice.reminded").lower()
    assert summarize_audit_action("custom.thing_done") == "Custom Thing Done"


def test_delete_request_persists_on_profile(db):
    ctx = _merchant_ctx(db)
    svc = PrivacyService()
    result = svc.request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id, reason="Leaving GTA")
    db.refresh(ctx.merchant)
    file = merchant_privacy_file(ctx.merchant)
    assert result["reference"].startswith("DSR-")
    assert file["status"] == "pending"
    assert file["delete_reference"] == result["reference"]
    assert file["delete_reason"] == "Leaving GTA"
    assert file["delete_requested_at"]
    assert "Keep this reference" in result["message"]

    again = svc.request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id)
    assert again["reference"] == result["reference"]
    count = (
        db.query(MerchantAuditLog)
        .filter(
            MerchantAuditLog.merchant_id == ctx.merchant.id,
            MerchantAuditLog.action == "privacy.delete_requested",
        )
        .count()
    )
    assert count == 1


def test_privacy_status_includes_english_logs(db):
    ctx = _merchant_ctx(db)
    svc = PrivacyService()
    svc.request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id)
    status = svc.privacy_status(db, ctx.merchant)
    assert status["status"] == "pending"
    assert status["recent_logs"][0]["summary"] == "Deletion requested"
    assert "payload" not in status["recent_logs"][0]

    snap = rbac_and_audit_snapshot(db, ctx.merchant.id, limit=10)
    assert snap["recent_audit_logs"][0]["summary"] == "Deletion requested"
    assert "rbac" in snap


def test_export_audit_logs_include_summary(db):
    ctx = _merchant_ctx(db)
    svc = PrivacyService()
    svc.request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id)
    payload = svc.export_merchant(db, ctx.merchant, actor_user_id=ctx.user.id)
    assert payload["audit_logs"][0]["summary"] == "Deletion requested"


@pytest.fixture
def admin_client(db, monkeypatch):
    monkeypatch.setattr("porterchain_api.routers.merchants.require_module", lambda ctx, module: None)
    admin = AdminContext(
        user=AdminUser(clerk_user_id="privacy-admin", email="ops@porterchain.com", role="super_admin"),
        role=parse_admin_role("super_admin"),
    )
    app.dependency_overrides[get_admin_context] = lambda: admin
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_admin_privacy_get_and_execute_english(admin_client, db):
    ctx = _merchant_ctx(db)
    db.commit()
    PrivacyService().request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id)

    missing = admin_client.get("/v1/admin/merchants/does-not-exist/privacy")
    assert missing.status_code == 404
    assert "not found" in missing.json()["detail"].lower()

    body = admin_client.get(f"/v1/admin/merchants/{ctx.merchant.id}/privacy").json()
    assert body["status"] == "pending"
    assert body["delete_reference"].startswith("DSR-")
    assert body["recent_logs"][0]["summary"] == "Deletion requested"

    blocked = admin_client.post(f"/v1/admin/merchants/{ctx.merchant.id}/privacy/execute")
    assert blocked.status_code == 400
    assert "Close this company first" in blocked.json()["detail"]
