"""AY — new seat first run: Clerk password, wait for ACTIVE, English roles, seat off stays off."""

from __future__ import annotations

import uuid

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.merchant_onboarding import (
    ensure_merchant_portal_signup,
    evaluate_merchant_onboarding,
)
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import ROLE_LABELS
from porterchain_api.merchant_models import Merchant, MerchantUser


def _claims(clerk_id: str, email: str) -> ClerkClaims:
    return ClerkClaims(clerk_user_id=clerk_id, email=email, clerk_app="merchant")


def _company(
    db,
    *,
    status: str = MerchantStatus.ACTIVE.value,
) -> Merchant:
    merchant = Merchant(
        status=status,
        company_name="First Run Co",
        email=f"owner_{uuid.uuid4().hex[:10]}@firstrun.test",
        payment_terms="NET_30",
    )
    db.add(merchant)
    db.flush()
    return merchant


def _reserved_seat(db, merchant: Merchant, *, role: str, email: str) -> MerchantUser:
    """Owner reserves a seat by email — no Clerk invite, clerk id stays pending."""
    seat = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=f"pending:{email}",
        email=email,
        role=role,
        is_active=True,
    )
    db.add(seat)
    db.commit()
    return seat


def test_reserved_seat_links_clerk_id_on_first_sign_in(db, settings) -> None:
    merchant = _company(db)
    email = f"dispatch_{uuid.uuid4().hex[:8]}@firstrun.test"
    seat = _reserved_seat(db, merchant, role=MerchantRole.OPS.value, email=email)
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    settings.clerk_dev_bypass = False

    ensure_merchant_portal_signup(db, _claims(clerk_id, email), settings=settings)

    db.refresh(seat)
    assert seat.clerk_user_id == clerk_id
    assert seat.merchant_id == merchant.id
    assert seat.role == MerchantRole.OPS.value


def test_seat_turned_off_stays_off_after_sign_in(db, settings) -> None:
    merchant = _company(db)
    email = f"off_{uuid.uuid4().hex[:8]}@firstrun.test"
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    seat = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=clerk_id,
        email=email,
        role=MerchantRole.OPS.value,
        is_active=False,
    )
    db.add(seat)
    db.commit()
    settings.clerk_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(clerk_id, email), settings=settings)

    db.refresh(seat)
    assert seat.is_active is False
    assert result["ready"] is False
    assert "team_access" in result["blockers"]
    step = next(s for s in result["steps"] if s["id"] == "team_access")
    assert step["complete"] is False
    assert "turned this seat off" in step["description"]


def test_active_company_new_seat_is_ready_for_dashboard(db, settings) -> None:
    merchant = _company(db, status=MerchantStatus.ACTIVE.value)
    email = f"ready_{uuid.uuid4().hex[:8]}@firstrun.test"
    _reserved_seat(db, merchant, role=MerchantRole.FINANCE.value, email=email)
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    settings.clerk_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(clerk_id, email), settings=settings)

    assert result["ready"] is True
    assert result["can_access_portal"] is True
    assert result["blockers"] == []
    assert result["role_label"] == "Accounting"


def test_onboarding_company_makes_every_seat_wait(db, settings) -> None:
    merchant = _company(db, status=MerchantStatus.ONBOARDING.value)
    email = f"wait_{uuid.uuid4().hex[:8]}@firstrun.test"
    _reserved_seat(db, merchant, role=MerchantRole.OPS.value, email=email)
    clerk_id = f"user_{uuid.uuid4().hex[:12]}"
    settings.clerk_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(clerk_id, email), settings=settings)

    assert result["ready"] is False
    assert result["blockers"] == ["admin_authorization"]
    assert result["status_label"] == "Onboarding"
    assert result["can_edit_company"] is False
    assert "/sign-up" in result["signup_url"]


def test_first_run_copy_never_shows_internal_role_ids(db, settings) -> None:
    merchant = _company(db, status=MerchantStatus.ONBOARDING.value)
    settings.clerk_dev_bypass = False
    for role in MerchantRole:
        email = f"role_{role.value}_{uuid.uuid4().hex[:6]}@firstrun.test"
        _reserved_seat(db, merchant, role=role.value, email=email)
        clerk_id = f"user_{uuid.uuid4().hex[:12]}"
        result = evaluate_merchant_onboarding(db, _claims(clerk_id, email), settings=settings)
        assert result["role_label"] == ROLE_LABELS[role]
        assert "merchant_" not in result["role_label"]
        for step in result["steps"]:
            assert "merchant_" not in step["label"]
            assert "merchant_" not in step["description"]
            assert "merchant_" not in step["status_label"]
