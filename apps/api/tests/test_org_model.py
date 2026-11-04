"""Doc 70: one Organisation model, capability packs, versioned operating profile, external refs."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.db import get_db
from porterchain_api.main import app
from porterchain_api.merchant_models import Merchant, ShopifyShop
from porterchain_api.org_engine import packs, service


def test_packs_defaults_and_subtypes():
    assert "rx_delivery" in packs.default_capabilities("small_shop", "pharmacy")
    assert "food_handling" in packs.default_capabilities("small_shop", "bakery_cake")
    with pytest.raises(ValueError):
        packs.default_capabilities("small_shop", "casino")
    with pytest.raises(ValueError):
        packs.business_type("spaceport")
    assert packs.default_profile("warehouse_3pl")["pickup_mode"] == "dock_appointment"
    assert "gs1_128" in packs.default_profile("warehouse_3pl")["barcode_formats"]
    for code, bt in packs.BUSINESS_TYPES.items():
        assert set(bt["capabilities"]) <= set(packs.CAPABILITIES), code
        packs.validate_profile(packs.default_profile(code))


def test_documents_matrix():
    assert "bol" not in packs.documents_for("small_shop", "bakery_cake")  # a bakery has no BOL
    assert packs.documents_for("warehouse_3pl")["bol"] == "C1"  # a warehouse sometimes does
    assert packs.documents_for("small_shop", "pharmacy")["rx_custody_log"] == "A"
    assert packs.documents_for("small_shop", "gift")["pod"] == "A"


def test_profile_versioning_and_external_refs(db):
    org = service.provision(db, display_name="Test Bakery", business_type="small_shop", subtype="bakery_cake")
    assert org.public_id.startswith("ORG-") and len(org.public_id) == 10
    assert service.has_capability(db, org.id, "food_handling")
    assert service.current_profile(db, org.id).version == 1
    p2 = service.set_profile(db, org.id, {"pickup_mode": "scheduled_daily", "pickup_params": {"cutoff": "11:00"}})
    assert p2.version == 2 and p2.label_mode == "ours"
    with pytest.raises(ValueError):
        service.set_profile(db, org.id, {"label_mode": "sticker"})
    a = service.upsert_external_ref(db, org_id=org.id, ref_type="order", ref_value=" 1001 ", entity_type="order", entity_id="o1")
    b = service.upsert_external_ref(db, org_id=org.id, ref_type="order", ref_value="1001", entity_type="order", entity_id="o2")
    assert a.id == b.id and b.entity_id == "o1"
    with pytest.raises(ValueError):
        service.set_capabilities(db, org.id, {"teleport": True})


def _merchant(db, name, shopify=False):
    m = Merchant(company_name=name, email=f"{uuid.uuid4().hex[:8]}@example.com", status="active")
    db.add(m)
    db.flush()
    if shopify:
        db.add(ShopifyShop(merchant_id=m.id, shop_domain=f"{uuid.uuid4().hex[:8]}.myshopify.com"))
        db.flush()
    return m


def test_backfill_keeps_ids_and_is_idempotent(db):
    shop = _merchant(db, "PCDC Test", shopify=True)
    plain = _merchant(db, "Corner Store")
    dry = service.backfill_from_merchants(db, dry_run=True)
    ids = {o["merchant_id"]: o for o in dry["orgs"]}
    assert ids[shop.id]["business_type"] == "shopify_merchant"
    assert ids[plain.id]["needs_review"] is True
    service.backfill_from_merchants(db, dry_run=False)
    from porterchain_api.org_engine.models import Organisation

    assert db.get(Organisation, shop.id).business_type == "shopify_merchant"
    again = service.backfill_from_merchants(db, dry_run=False)
    assert shop.id not in {o["merchant_id"] for o in again["orgs"]}


def test_admin_api(db):
    ctx = AdminContext(user=AdminUser(auth_subject="org-admin", email="o@porterchain.com", role="super_admin"), role=parse_admin_role("super_admin"))
    app.dependency_overrides[get_admin_context] = lambda: ctx
    app.dependency_overrides[get_db] = lambda: db
    try:
        c = TestClient(app)
        assert len(c.get("/v1/admin/orgs/business-types").json()["business_types"]) == 8
        r = c.post("/v1/admin/orgs", json={"display_name": "Rx Corner", "business_type": "small_shop", "subtype": "pharmacy"})
        assert r.status_code == 201 and r.json()["capabilities"]["rx_delivery"] is True
        oid = r.json()["public_id"]
        r = c.put(f"/v1/admin/orgs/{oid}/operating-profile", json={"tracking_mode": "both"})
        assert r.json()["profile"]["version"] == 2
        assert c.put(f"/v1/admin/orgs/{oid}/operating-profile", json={"pickup_mode": "teleport"}).status_code == 422
        r = c.put(f"/v1/admin/orgs/{oid}/capabilities", json={"capabilities": {"same_day": False}})
        assert r.json()["capabilities"]["same_day"] is False
        r = c.put(f"/v1/admin/orgs/{oid}/type", json={"business_type": "warehouse_3pl", "reset_capabilities": True})
        assert r.json()["capabilities"]["pallet"] is True and r.json()["capabilities"]["rx_delivery"] is False
        assert c.post("/v1/admin/orgs/backfill-from-merchants", json={"dry_run": True}).status_code == 200
        c.post("/v1/admin/orgs", json={"display_name": "Bloom Florist", "business_type": "small_shop", "subtype": "flowers"})
        lst = c.get("/v1/admin/orgs", params={"q": "bloom"}).json()
        assert lst["total"] == 1 and lst["items"][0]["display_name"] == "Bloom Florist"
        assert lst["counts"]["by_type"]["small_shop"] >= 1 and lst["counts"]["all"] >= 2
        assert c.get("/v1/admin/orgs", params={"business_type": "warehouse_3pl", "limit": 1, "offset": 0}).json()["total"] >= 1
        assert c.get("/v1/admin/orgs", params={"status": "no-such"}).json()["items"] == []
        ctx2 = AdminContext(user=AdminUser(auth_subject="d", email="d@porterchain.com", role="dispatcher"), role=parse_admin_role("dispatcher"))
        app.dependency_overrides[get_admin_context] = lambda: ctx2
        assert c.get(f"/v1/admin/orgs/{oid}").status_code == 200
        assert c.post("/v1/admin/orgs", json={"display_name": "x", "business_type": "small_shop"}).status_code == 403
    finally:
        app.dependency_overrides.clear()
