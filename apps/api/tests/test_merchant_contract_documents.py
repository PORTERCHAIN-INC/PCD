"""Merchant sees only its own signed contract / rate sheet from the staff vault."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.config import get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.main import app
from porterchain_api.merchant_engine.account_ops import documents
from porterchain_api.merchant_engine.rbac import MerchantContext
from porterchain_api.merchant_models import Merchant, MerchantAuditLog, MerchantDocument, MerchantUser

PDF = b"%PDF-1.4 contract"


def _ctx(db, role=MerchantRole.OWNER) -> MerchantContext:
    s = uuid4().hex[:8]
    m = Merchant(company_name=f"Doc Co {s}", email=f"d-{s}@test.local", status=MerchantStatus.ACTIVE.value)
    db.add(m)
    db.flush()
    u = MerchantUser(merchant_id=m.id, clerk_user_id=f"c_{s}", email=f"u-{s}@test.local", role=role.value)
    db.add(u)
    db.flush()
    return MerchantContext(merchant=m, user=u, role=role)


def _doc(db, merchant_id, kind) -> MerchantDocument:
    d = MerchantDocument(merchant_id=merchant_id, kind=kind, filename=f"{kind}.pdf",
                         content_type="application/pdf", size_bytes=len(PDF), sha256="x" * 64, content=PDF,
                         note="staff only", uploaded_by="admin:1")
    db.add(d)
    db.flush()
    return d


def test_merchant_sees_contract_not_staff_only_docs_and_not_other_merchants(db, settings, monkeypatch):
    from fastapi import HTTPException

    from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS

    def _role_only(ctx, module):  # org-permission lookup off; same role matrix
        if ctx.role not in MODULE_PERMISSIONS[module]:
            raise HTTPException(status_code=403, detail="forbidden")

    monkeypatch.setattr("porterchain_api.routers.merchant.settings.require_module", _role_only)
    holder: dict = {}
    app.dependency_overrides[get_merchant_context] = lambda: holder["ctx"]
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    try:
        ctx, other = _ctx(db), _ctx(db)
        contract = _doc(db, ctx.merchant.id, "signed_contract")
        coi = _doc(db, ctx.merchant.id, "insurance_coi")
        foreign = _doc(db, other.merchant.id, "signed_contract")
        db.commit()
        holder["ctx"] = ctx
        resp = client.get("/v1/merchant/contract-documents")
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        assert [i["id"] for i in items] == [contract.id]
        assert "uploaded_by" not in items[0] and "note" not in items[0]
        r = client.get(f"/v1/merchant/contract-documents/{contract.id}/download")
        assert r.status_code == 200 and r.content == PDF
        assert r.headers["cache-control"] == "no-store"
        assert client.get(f"/v1/merchant/contract-documents/{coi.id}/download").status_code == 404
        assert client.get(f"/v1/merchant/contract-documents/{foreign.id}/download").status_code == 404
        assert db.query(MerchantAuditLog).filter_by(resource_id=contract.id, action="document.downloaded").count() == 1
        holder["ctx"] = _ctx(db, MerchantRole.OPS)
        assert client.get("/v1/merchant/contract-documents").status_code == 403
    finally:
        app.dependency_overrides.clear()


def test_visible_kinds_are_contract_and_rate_sheet_only():
    assert documents.MERCHANT_VISIBLE_KINDS == {"signed_contract", "rate_sheet"}
