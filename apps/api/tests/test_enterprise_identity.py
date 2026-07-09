"""Enterprise identity tests (§11.2)."""

from __future__ import annotations

from uuid import uuid4

from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.domain.admin_states import AdminRole
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_models import Merchant


def _admin_ctx(db):
    from porterchain_api.admin_models import AdminUser

    suffix = uuid4().hex[:8]
    user = AdminUser(
        clerk_user_id=f"admin_{suffix}",
        email=f"admin-{suffix}@test.local",
        role=AdminRole.SUPER_ADMIN.value,
    )
    db.add(user)
    db.flush()
    return AdminContext(user=user, role=AdminRole.SUPER_ADMIN)


def test_parent_subsidiary_link(db):
    parent = Merchant(
        company_name="Parent Co",
        email=f"parent-{uuid4().hex[:6]}@test.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
    )
    child = Merchant(
        company_name="Child Co",
        email=f"child-{uuid4().hex[:6]}@test.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="NET_30",
    )
    db.add(parent)
    db.add(child)
    db.flush()

    svc = AdminMerchantService()
    ctx = _admin_ctx(db)
    svc.update_merchant_terms(db, ctx, child.id, parent_merchant_id=parent.id, support_tier="priority")
    db.refresh(child)

    assert child.parent_merchant_id == parent.id
    assert child.profile["enterprise"]["support_tier"] == "priority"
    subs = svc.list_subsidiaries(db, parent.id)
    assert len(subs) == 1
    assert subs[0].id == child.id


def test_payment_terms_update(db):
    merchant = Merchant(
        company_name="Terms Co",
        email=f"terms-{uuid4().hex[:6]}@test.local",
        status=MerchantStatus.ACTIVE.value,
        payment_terms="IMMEDIATE",
    )
    db.add(merchant)
    db.flush()
    svc = AdminMerchantService()
    ctx = _admin_ctx(db)
    svc.update_merchant_terms(db, ctx, merchant.id, payment_terms="NET_45")
    db.refresh(merchant)
    assert merchant.payment_terms == "NET_45"
