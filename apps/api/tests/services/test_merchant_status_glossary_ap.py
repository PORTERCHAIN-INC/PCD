"""AP — one status glossary for portal, onboarding, and admin."""

from __future__ import annotations

from types import SimpleNamespace

from porterchain_api.admin_engine.merchant360_service import Merchant360Service
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding
from porterchain_api.domain.catalog_labels import (
    invite_status_label,
    merchant_status_label,
    onboarding_phase_label,
    onboarding_step_status_label,
    seat_status_label,
)
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.company_file import merchant_status_label as company_file_label
from porterchain_api.merchant_engine.team_service import seat_status, serialize_member


def test_company_status_words_are_english() -> None:
    assert merchant_status_label("PENDING") == "Pending"
    assert merchant_status_label("ONBOARDING") == "Onboarding"
    assert merchant_status_label("ACTIVE") == "Active"
    assert merchant_status_label("SUSPENDED") == "Suspended"
    assert merchant_status_label("CLOSED") == "Closed"
    assert merchant_status_label("") == "Unknown"
    assert company_file_label("ACTIVE") == merchant_status_label("ACTIVE")


def test_onboarding_and_seat_words() -> None:
    assert onboarding_phase_label("needs_invite") == "Needs invite"
    assert onboarding_phase_label("awaiting_clerk") == "Awaiting sign-in"
    assert onboarding_phase_label("needs_approval") == "Needs approval"
    assert seat_status_label("pending") == "Pending"
    assert seat_status_label("active") == "Active"
    assert seat_status_label("off") == "Off"
    assert invite_status_label("not_invited") == "Not invited"
    assert onboarding_step_status_label("inactive") == "Off"
    assert onboarding_step_status_label("onboarding", complete=False) == "Onboarding"
    assert onboarding_step_status_label("pending", complete=True) == "Complete"


def test_360_row_uses_glossary(db, merchant_ctx) -> None:
    merchant_ctx.merchant.status = MerchantStatus.ONBOARDING.value
    db.commit()
    row = Merchant360Service()._row(db, merchant_ctx.merchant)
    assert row["status"] == "ONBOARDING"
    assert row["status_label"] == "Onboarding"


def test_onboarding_payload_uses_same_words(db, settings, merchant_ctx) -> None:
    from porterchain_api.auth.claims import ClerkClaims

    merchant_ctx.merchant.status = MerchantStatus.ONBOARDING.value
    db.commit()
    claims = ClerkClaims(
        clerk_user_id=merchant_ctx.user.clerk_user_id,
        email=merchant_ctx.user.email,
        clerk_app="merchant",
    )
    settings.clerk_dev_bypass = False
    result = evaluate_merchant_onboarding(db, claims, settings=settings)
    assert result["status_label"] == "Onboarding"
    auth = next(s for s in result["steps"] if s["id"] == "admin_authorization")
    assert auth["status"] == "onboarding"
    assert auth["status_label"] == "Onboarding"
    assert auth["label"] == "Onboarding"


def test_seat_serialize_uses_glossary() -> None:
    pending = SimpleNamespace(
        id="u1",
        email="ops@test.com",
        role="merchant_ops",
        is_active=True,
        clerk_user_id="pending:ops@test.com",
        created_at=None,
    )
    off = SimpleNamespace(id="u2", email="off@test.com", role="merchant_readonly", is_active=False, clerk_user_id="user_1", created_at=None)
    assert seat_status(pending) == "pending"
    assert serialize_member(pending)["seat_status_label"] == "Pending"
    assert serialize_member(off)["seat_status_label"] == "Off"
