"""ONB-M — merchant onboarding gate blockers + portal client wiring.

Happy-path evaluate coverage already lives in test_merchant_onboarding_*.py.
This file closes the incomplete / AccessGate contract gap CodeGraph flagged.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser

REPO = Path(__file__).resolve().parents[3]
MERCHANT_SRC = REPO / "apps" / "merchant-portal" / "src"


def _seat(
    db,
    *,
    status: str,
    role: str = MerchantRole.OWNER.value,
    is_active: bool = True,
    vertical: str | None = "wholesale",
) -> tuple[str, Merchant]:
    suffix = uuid.uuid4().hex[:10]
    clerk_id = f"user_onb_m_{suffix}"
    merchant = Merchant(
        status=status,
        company_name=f"ONB Co {suffix}",
        email=f"onb-{suffix}@test.local",
        phone="+14165550100",
        legal_name=f"ONB Legal {suffix}",
        hst_number="123456789RT0001",
        profile={
            "vertical": vertical,
            "billing_address": {"formatted": "100 King St W, Toronto", "postal": "M5X 1A1"},
        },
    )
    db.add(merchant)
    db.flush()
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=clerk_id,
            email=merchant.email,
            role=role,
            is_active=is_active,
        )
    )
    db.commit()
    return clerk_id, merchant


def test_evaluate_blocks_pending_admin_authorization(db, settings) -> None:
    clerk_id, merchant = _seat(db, status=MerchantStatus.PENDING.value)
    settings.clerk_dev_bypass = False
    claims = ClerkClaims(
        clerk_user_id=clerk_id, email=merchant.email, clerk_app="merchant"
    )
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is False
    assert result["can_access_portal"] is False
    assert "admin_authorization" in result["blockers"]
    assert result["merchant_id"] == merchant.id


def test_evaluate_blocks_onboarding_status_until_active(db, settings) -> None:
    clerk_id, merchant = _seat(db, status=MerchantStatus.ONBOARDING.value)
    settings.clerk_dev_bypass = False
    claims = ClerkClaims(
        clerk_user_id=clerk_id, email=merchant.email, clerk_app="merchant"
    )
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is False
    assert "admin_authorization" in result["blockers"]


def test_evaluate_blocks_suspended_and_closed(db, settings) -> None:
    settings.clerk_dev_bypass = False

    suspended_id, suspended = _seat(db, status=MerchantStatus.SUSPENDED.value)
    sus = evaluate_merchant_onboarding(
        db,
        ClerkClaims(
            clerk_user_id=suspended_id, email=suspended.email, clerk_app="merchant"
        ),
        settings=settings,
    )
    assert "account_suspended" in sus["blockers"]
    assert sus["can_access_portal"] is False

    closed_id, closed = _seat(db, status=MerchantStatus.CLOSED.value)
    clo = evaluate_merchant_onboarding(
        db,
        ClerkClaims(clerk_user_id=closed_id, email=closed.email, clerk_app="merchant"),
        settings=settings,
    )
    assert "merchant_closed" in clo["blockers"]
    assert clo["can_access_portal"] is False


def test_evaluate_blocks_inactive_seat(db, settings) -> None:
    clerk_id, merchant = _seat(
        db, status=MerchantStatus.ACTIVE.value, is_active=False
    )
    settings.clerk_dev_bypass = False
    result = evaluate_merchant_onboarding(
        db,
        ClerkClaims(clerk_user_id=clerk_id, email=merchant.email, clerk_app="merchant"),
        settings=settings,
    )
    assert result["ready"] is False
    assert "team_access" in result["blockers"]


def test_evaluate_auto_signup_still_blocks_until_admin_active(db, settings) -> None:
    """ensure_merchant_portal_signup creates a seat, but portal stays closed until ACTIVE."""
    settings.clerk_dev_bypass = False
    claims = ClerkClaims(
        clerk_user_id=f"user_orphan_{uuid.uuid4().hex[:8]}",
        email=f"orphan-{uuid.uuid4().hex[:6]}@test.local",
        clerk_app="merchant",
    )
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["ready"] is False
    assert result["can_access_portal"] is False
    # Signup provisions a seat; activation is the remaining gate.
    assert result["merchant_id"] is not None
    assert "admin_authorization" in result["blockers"]
    assert "merchant_provisioned" not in result["blockers"]


def test_merchant_portal_onboarding_client_contract() -> None:
    onboarding = (MERCHANT_SRC / "lib/onboarding.ts").read_text(encoding="utf-8")
    gate = (MERCHANT_SRC / "components/MerchantAccessGate.tsx").read_text(encoding="utf-8")
    assert "/v1/auth/merchant/onboarding" in onboarding
    assert "fetchMerchantOnboarding" in onboarding
    assert "/v1/auth/merchant/onboarding/vertical" in onboarding
    assert "fetchMerchantOnboarding" in gate
    assert "onNeedOnboarding" in gate
    assert 'router.replace("/onboarding")' in gate
    assert "isPendingMerchantPath" in gate
