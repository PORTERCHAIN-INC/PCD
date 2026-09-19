"""Merchant self-serve referrals."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.collaboration_engine.lead_ops import merchant_referral_overview
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantUser


def _merchant_ctx(db) -> MerchantContext:
    suffix = uuid4().hex[:8]
    merchant = Merchant(
        company_name=f"Refer Co {suffix}",
        email=f"refer-{suffix}@test.local",
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


def test_merchant_referral_overview_share_url(db, settings) -> None:
    ctx = _merchant_ctx(db)
    db.commit()
    out = merchant_referral_overview(db, merchant_id=ctx.merchant.id, settings=settings)
    assert out["merchant_id"] == ctx.merchant.id
    assert f"ref={ctx.merchant.id}" in out["share_url"]
    assert "merchant_referral" in out["share_url"]
    assert out["credit_cents"] == int(settings.referral_credit_cents or 0)
    assert out["credits"] == []
    assert out["referred_leads"] == []


def test_merchant_referrals_http(db, settings, monkeypatch) -> None:
    holder: dict = {}
    monkeypatch.setattr(
        "porterchain_api.routers.merchant.referrals.require_module",
        lambda ctx, module: None,
    )
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx = _merchant_ctx(db)
        db.commit()
        holder["ctx"] = ctx

        overview = client.get("/v1/merchant/referrals")
        assert overview.status_code == 200
        body = overview.json()
        assert body["merchant_id"] == ctx.merchant.id
        assert f"ref={ctx.merchant.id}" in body["share_url"]

        created = client.post(
            "/v1/merchant/referrals",
            json={
                "company_name": "Warm Intro Ltd",
                "email": f"warm-{uuid4().hex[:6]}@example.com",
                "contact_name": "Alex",
                "notes": "Met at market",
            },
        )
        assert created.status_code == 201, created.text
        lead = created.json()
        assert lead["referred_by_merchant_id"] == ctx.merchant.id
        assert lead["channel"] == "merchant_referral"

        again = client.get("/v1/merchant/referrals")
        assert again.status_code == 200
        assert len(again.json()["referred_leads"]) >= 1
    finally:
        app.dependency_overrides.clear()
