"""AY — new seat first run: Keycloak password, wait for ACTIVE, English roles, seat off stays off."""

from __future__ import annotations

import uuid

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.merchant_onboarding import (
    ensure_merchant_portal_signup,
    evaluate_merchant_onboarding,
)
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import ROLE_LABELS
from porterchain_api.merchant_models import Merchant, MerchantUser


def _claims(subject_ref: str, email: str) -> IdentityClaims:
    return IdentityClaims(auth_subject=subject_ref, email=email, idp_app="merchant")


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
    """Owner reserves a seat by email — no Keycloak invite, keycloak id stays pending."""
    seat = MerchantUser(
        merchant_id=merchant.id,
        auth_subject=f"pending:{email}",
        email=email,
        role=role,
        is_active=True,
    )
    db.add(seat)
    db.commit()
    return seat


def test_reserved_seat_links_idp_id_on_first_sign_in(db, settings) -> None:
    merchant = _company(db)
    email = f"dispatch_{uuid.uuid4().hex[:8]}@firstrun.test"
    seat = _reserved_seat(db, merchant, role=MerchantRole.OPS.value, email=email)
    subject_ref = f"user_{uuid.uuid4().hex[:12]}"
    settings.auth_dev_bypass = False

    ensure_merchant_portal_signup(db, _claims(subject_ref, email), settings=settings)

    db.refresh(seat)
    assert seat.auth_subject == subject_ref
    assert seat.merchant_id == merchant.id
    assert seat.role == MerchantRole.OPS.value


def test_second_company_pending_owner_claimed_when_already_linked_elsewhere(db, settings) -> None:
    """Kaylulu-class bug: OTP linked auto-company B; Admin reserved Owner on A stays pending."""
    auto = _company(db, status=MerchantStatus.ACTIVE.value)
    kaylulu = _company(db, status=MerchantStatus.ACTIVE.value)
    email = f"tracy_{uuid.uuid4().hex[:8]}@firstrun.test"
    subject_ref = f"user_{uuid.uuid4().hex[:12]}"
    linked = MerchantUser(
        merchant_id=auto.id,
        auth_subject=subject_ref,
        email=email,
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    pending = MerchantUser(
        merchant_id=kaylulu.id,
        auth_subject=f"pending:{email}",
        email=email,
        role=MerchantRole.OWNER.value,
        is_active=True,
    )
    db.add_all([linked, pending])
    db.commit()
    settings.auth_dev_bypass = False

    ensure_merchant_portal_signup(db, _claims(subject_ref, email), settings=settings)

    db.refresh(pending)
    db.refresh(linked)
    assert linked.auth_subject == subject_ref
    assert pending.auth_subject == subject_ref


def test_seat_turned_off_stays_off_after_sign_in(db, settings) -> None:
    merchant = _company(db)
    email = f"off_{uuid.uuid4().hex[:8]}@firstrun.test"
    subject_ref = f"user_{uuid.uuid4().hex[:12]}"
    seat = MerchantUser(
        merchant_id=merchant.id,
        auth_subject=subject_ref,
        email=email,
        role=MerchantRole.OPS.value,
        is_active=False,
    )
    db.add(seat)
    db.commit()
    settings.auth_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(subject_ref, email), settings=settings)

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
    subject_ref = f"user_{uuid.uuid4().hex[:12]}"
    settings.auth_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(subject_ref, email), settings=settings)

    assert result["ready"] is True
    assert result["can_access_portal"] is True
    assert result["blockers"] == []
    assert result["role_label"] == "Accounting"


def test_onboarding_company_makes_every_seat_wait(db, settings) -> None:
    merchant = _company(db, status=MerchantStatus.ONBOARDING.value)
    email = f"wait_{uuid.uuid4().hex[:8]}@firstrun.test"
    _reserved_seat(db, merchant, role=MerchantRole.OPS.value, email=email)
    subject_ref = f"user_{uuid.uuid4().hex[:12]}"
    settings.auth_dev_bypass = False

    result = evaluate_merchant_onboarding(db, _claims(subject_ref, email), settings=settings)

    assert result["ready"] is False
    assert result["blockers"] == ["admin_authorization"]
    assert result["status_label"] == "Onboarding"
    assert result["can_edit_company"] is False
    assert "/sign-up" in result["signup_url"]


def test_first_run_copy_never_shows_internal_role_ids(db, settings) -> None:
    merchant = _company(db, status=MerchantStatus.ONBOARDING.value)
    settings.auth_dev_bypass = False
    for role in MerchantRole:
        email = f"role_{role.value}_{uuid.uuid4().hex[:6]}@firstrun.test"
        _reserved_seat(db, merchant, role=role.value, email=email)
        subject_ref = f"user_{uuid.uuid4().hex[:12]}"
        result = evaluate_merchant_onboarding(db, _claims(subject_ref, email), settings=settings)
        assert result["role_label"] == ROLE_LABELS[role]
        assert "merchant_" not in result["role_label"]
        for step in result["steps"]:
            assert "merchant_" not in step["label"]
            assert "merchant_" not in step["description"]
            assert "merchant_" not in step["status_label"]
