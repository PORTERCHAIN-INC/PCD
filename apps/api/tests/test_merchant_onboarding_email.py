"""Merchant onboarding resolves email when Clerk JWT omits email claim."""

from __future__ import annotations

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding, resolve_merchant_contact
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_resolve_merchant_contact_from_merchant_user(db, settings) -> None:
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name="Pareva Logistics",
        email="parevalogistics@gmail.com",
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id="user_merchant_test",
            email="parevalogistics@gmail.com",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()

    claims = ClerkClaims(clerk_user_id="user_merchant_test", email=None, clerk_app="merchant")
    assert resolve_merchant_contact(db, claims, settings) == "parevalogistics@gmail.com"


def test_evaluate_merchant_onboarding_without_jwt_email(db, settings) -> None:
    merchant = Merchant(
        status=MerchantStatus.ACTIVE.value,
        company_name="Pareva Logistics",
        email="parevalogistics@gmail.com",
        profile={"vertical": "wholesale"},
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id="user_merchant_onboard",
            email="parevalogistics@gmail.com",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()

    settings.clerk_dev_bypass = False
    claims = ClerkClaims(clerk_user_id="user_merchant_onboard", email=None, clerk_app="merchant")
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["merchant_id"] == merchant.id
    assert result["company_name"] == "Pareva Logistics"
    assert result["can_access_portal"] is True
