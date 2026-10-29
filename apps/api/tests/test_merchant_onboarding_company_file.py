"""Onboarding is a company file + wait — not a vertical lock on ACTIVE users."""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.merchant_onboarding import (
    evaluate_merchant_onboarding,
    save_merchant_company_file,
)
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.company_file import company_file_missing, merchant_status_label
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest


def _claims(subject_ref: str, email: str) -> IdentityClaims:
    return IdentityClaims(auth_subject=subject_ref, email=email, clerk_app="merchant")


def _seat(
    db,
    *,
    status: str,
    role: str = MerchantRole.OWNER.value,
    legal_name: str | None = None,
    phone: str | None = None,
    hst: str | None = None,
    billing: dict | None = None,
    vertical: str | None = None,
) -> tuple[Merchant, MerchantUser, IdentityClaims]:
    subject_ref = f"user_onboard_{uuid.uuid4().hex[:10]}"
    email = f"{subject_ref}@onboard.test"
    profile = {"vertical": vertical} if vertical else {}
    merchant = Merchant(
        status=status,
        company_name="Onboard Co",
        email=email,
        legal_name=legal_name,
        phone=phone,
        hst_number=hst,
        billing_address=billing,
        profile=profile,
    )
    db.add(merchant)
    db.flush()
    user = MerchantUser(
        merchant_id=merchant.id,
        auth_subject=subject_ref,
        email=email,
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    return merchant, user, _claims(subject_ref, email)


def test_status_glossary_matches_admin_words() -> None:
    assert merchant_status_label("PENDING") == "Pending"
    assert merchant_status_label("ONBOARDING") == "Onboarding"
    assert merchant_status_label("ACTIVE") == "Active"
    assert merchant_status_label("SUSPENDED") == "Suspended"
    assert merchant_status_label("CLOSED") == "Closed"


def test_active_without_vertical_or_hst_can_open_portal(db, settings) -> None:
    _merchant, _user, claims = _seat(db, status=MerchantStatus.ACTIVE.value)
    settings.auth_dev_bypass = False
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is True
    assert result["can_access_portal"] is True
    assert "business_vertical" not in result["blockers"]
    assert "company_profile" not in result["blockers"]
    assert result["completeness"]["complete"] is False
    assert "hst_number" in result["completeness"]["missing"]
    assert result["role_label"] == "Owner"
    assert result["status_label"] == "Active"


def test_onboarding_owner_waits_but_can_edit(db, settings) -> None:
    _merchant, _user, claims = _seat(db, status=MerchantStatus.ONBOARDING.value)
    settings.auth_dev_bypass = False
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is False
    assert result["blockers"] == ["admin_authorization"]
    assert result["can_edit_company"] is True
    assert result["status_label"] == "Onboarding"
    assert "/sign-up" in result["signup_url"]


def test_dispatcher_not_blocked_by_missing_hst(db, settings) -> None:
    _merchant, _user, claims = _seat(
        db,
        status=MerchantStatus.ACTIVE.value,
        role=MerchantRole.OPS.value,
    )
    settings.auth_dev_bypass = False
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is True
    assert result["role_label"] == "Dispatcher"
    assert result["can_edit_company"] is False
    assert "HST number" in result["completeness"]["missing_labels"]


def test_onboarding_owner_saves_company_file(db, settings) -> None:
    merchant, _user, claims = _seat(db, status=MerchantStatus.ONBOARDING.value)
    settings.auth_dev_bypass = False
    result = save_merchant_company_file(
        db,
        claims,
        MerchantProfileUpdateRequest(
            legal_name="Onboard Co Inc.",
            phone="4165550100",
            hst_number=f"{uuid.uuid4().int % 10**9:09d}RT0001",
            billing_address={"formatted": "100 Queen St W, Toronto, ON"},
        ),
        settings=settings,
    )
    db.refresh(merchant)
    assert merchant.legal_name == "Onboard Co Inc."
    assert merchant.phone == "4165550100"
    assert company_file_missing(merchant) == []
    assert result["completeness"]["complete"] is True
    assert result["ready"] is False


def test_dispatcher_cannot_save_company_file(db, settings) -> None:
    _merchant, _user, claims = _seat(
        db,
        status=MerchantStatus.ONBOARDING.value,
        role=MerchantRole.OPS.value,
    )
    settings.auth_dev_bypass = False
    with pytest.raises(HTTPException) as exc:
        save_merchant_company_file(
            db,
            claims,
            MerchantProfileUpdateRequest(legal_name="Nope Inc."),
            settings=settings,
        )
    assert exc.value.status_code == 403
    assert "owner" in str(exc.value.detail).lower()
