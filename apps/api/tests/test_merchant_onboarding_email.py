"""Merchant onboarding resolves Keycloak-attested email when JWT omits email claim."""

from __future__ import annotations

import uuid
from unittest.mock import patch

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding, resolve_merchant_contact
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser


def test_resolve_merchant_contact_from_jwt() -> None:
    claims = IdentityClaims(
        auth_subject="user_merchant_jwt",
        email="parevalogistics@gmail.com",
        idp_app="merchant",
    )
    assert resolve_merchant_contact(None, claims, None) == "parevalogistics@gmail.com"


def test_resolve_merchant_contact_never_trusts_db(db, settings) -> None:
    """DB persona email must not substitute for Keycloak identity email."""
    subject_ref = f"user_merchant_db_{uuid.uuid4().hex[:10]}"
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
            auth_subject=subject_ref,
            email="parevalogistics@gmail.com",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()

    claims = IdentityClaims(auth_subject=subject_ref, email=None, idp_app="merchant")
    with patch(
        "porterchain_api.auth.email_identity.resolve_verified_idp_email",
        side_effect=PermissionError("idp_email_required"),
    ):
        assert resolve_merchant_contact(db, claims, settings) is None


def test_resolve_merchant_contact_from_idp_backend(db, settings) -> None:
    claims = IdentityClaims(auth_subject="user_merchant_backend", email=None, idp_app="merchant")
    with patch(
        "porterchain_api.auth.email_identity.resolve_verified_idp_email",
        return_value="parevalogistics@gmail.com",
    ):
        assert resolve_merchant_contact(db, claims, settings) == "parevalogistics@gmail.com"


def test_evaluate_merchant_onboarding_with_idp_email(db, settings) -> None:
    subject_ref = f"user_merchant_onboard_{uuid.uuid4().hex[:10]}"
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
            auth_subject=subject_ref,
            email="parevalogistics@gmail.com",
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()

    settings.auth_dev_bypass = False
    claims = IdentityClaims(
        auth_subject=subject_ref,
        email="parevalogistics@gmail.com",
        idp_app="merchant",
    )
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["merchant_id"] == merchant.id
    assert result["company_name"] == "Pareva Logistics"
    assert result["can_access_portal"] is True
