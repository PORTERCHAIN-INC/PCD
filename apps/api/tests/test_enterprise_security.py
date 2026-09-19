"""Enterprise security tests (§11.1)."""

from __future__ import annotations

from uuid import uuid4

from porterchain_api.compliance_engine.privacy_service import PrivacyService
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.platform.health import public_status
from porterchain_api.platform.rate_limit import _check_rate


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


def test_merchant_privacy_export_shape(db):
    ctx = _merchant_ctx(db)
    svc = PrivacyService()
    payload = svc.export_merchant(db, ctx.merchant, actor_user_id=ctx.user.id)
    assert payload["subject_type"] == "merchant"
    assert payload["merchant_id"] == ctx.merchant.id
    assert "profile" in payload
    assert "team" in payload


def test_merchant_delete_request_reference(db):
    ctx = _merchant_ctx(db)
    svc = PrivacyService()
    result = svc.request_merchant_deletion(db, ctx.merchant, actor_user_id=ctx.user.id)
    assert result["status"] == "received"
    assert result["reference"].startswith("DSR-")


def test_rate_limit_fail_closed_on_redis_error(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise ConnectionError("redis down")

    monkeypatch.setattr("porterchain_shared.redis_client.get_redis_client", _boom)
    allowed, current, error = _check_rate("k", 1, 10)
    assert not allowed
    assert error


def test_public_status_shape(db, settings):
    payload = public_status(db, settings)
    assert payload["service"] == "porterchain"
    assert "components" in payload
    assert "api" in payload["components"]
