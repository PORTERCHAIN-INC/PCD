"""DB tests: dedupe flag on create paths, review queue, merge + undo, HST constraint."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from porterchain_api.merchant_engine import merchant_merge as mm
from porterchain_api.merchant_engine.provision import create_onboarding_merchant
from porterchain_api.merchant_models import Merchant, MerchantMerge, MerchantUser, ShopifyShop

CTX = SimpleNamespace(user=SimpleNamespace(id="test-admin"))


def _u() -> str:
    return uuid.uuid4().hex[:8]


@pytest.fixture
def pair(db):
    tag = _u()
    orig = create_onboarding_merchant(db, company_name=f"Kaylulu{tag}", email=f"tracy{tag}@gmail.com")
    db.add(MerchantUser(merchant_id=orig.id, clerk_user_id=f"user_{tag}", email=f"tracy{tag}@gmail.com", role="merchant_owner"))
    dup = create_onboarding_merchant(
        db, company_name=f"Kaylulu{tag} Inc.", email=f"hello@kaylulu{tag}.ca", dedupe_source="admin_create"
    )
    db.add(MerchantUser(merchant_id=dup.id, clerk_user_id=f"pending:hello@kaylulu{tag}.ca", email=f"hello@kaylulu{tag}.ca", role="merchant_owner"))
    db.add(ShopifyShop(merchant_id=dup.id, shop_domain=f"{tag}.myshopify.com", auto_dispatch=False))
    db.commit()
    return orig, dup


def test_create_path_flags_duplicate_without_linking(db, pair):
    orig, dup = pair
    flag = dup.profile["possible_duplicate_of"]
    assert flag["merchant_id"] == orig.id and flag["status"] == "open" and flag["source"] == "admin_create"
    assert "email_domain_is_name" in flag["reasons"]
    assert dup.id != orig.id  # created separately; nothing auto-joined


def test_unrelated_create_not_flagged(db):
    m = create_onboarding_merchant(db, company_name=f"Zed{_u()} Freight", email=f"a{_u()}@zedfreight.ca", dedupe_source="portal_signup")
    assert "possible_duplicate_of" not in (m.profile or {})


def test_queue_lists_then_keep_separate(db, pair):
    orig, dup = pair
    item = next(i for i in mm.list_duplicate_queue(db) if i["merchant_id"] == dup.id)
    assert item["match_merchant_id"] == orig.id
    assert item["preview"].get("merchant_users") == 1 and item["preview"].get("shopify_shops") == 1
    mm.keep_separate(db, CTX, dup.id)
    assert all(i["merchant_id"] != dup.id for i in mm.list_duplicate_queue(db))


def test_merge_moves_everything_and_undo_restores(db, pair):
    orig, dup = pair
    out = mm.merge_merchants(db, CTX, dup.id, orig.id)
    assert out["moved"]["merchant_users"] == 1 and out["moved"]["shopify_shops"] == 1
    assert db.query(MerchantUser).filter_by(merchant_id=orig.id).count() == 2
    assert db.query(ShopifyShop).filter_by(merchant_id=orig.id).count() == 1
    db.expire_all()
    assert db.query(Merchant).filter_by(id=dup.id).first() is None  # soft-deleted, hidden
    assert all(i["merchant_id"] != dup.id for i in mm.list_duplicate_queue(db))

    mm.undo_merge(db, CTX, out["merge_id"])
    db.expire_all()
    assert db.query(Merchant).filter_by(id=dup.id).first() is not None
    assert db.query(MerchantUser).filter_by(merchant_id=dup.id).count() == 1
    assert db.query(ShopifyShop).filter_by(merchant_id=dup.id).count() == 1
    assert db.get(MerchantMerge, out["merge_id"]).status == "undone"
    with pytest.raises(ValueError):
        mm.undo_merge(db, CTX, out["merge_id"])


def test_merge_self_refused(db, pair):
    with pytest.raises(ValueError):
        mm.merge_merchants(db, CTX, pair[0].id, pair[0].id)


def test_hst_unique_normalized(db):
    n = str(uuid.uuid4().int)[:9]
    create_onboarding_merchant(db, company_name="A", email=f"a{_u()}@a.ca", hst_number=f"{n} RT0001")
    db.commit()
    with pytest.raises(IntegrityError):
        create_onboarding_merchant(db, company_name="B", email=f"b{_u()}@b.ca", hst_number=f"{n}RT0001")
        db.commit()
    db.rollback()
