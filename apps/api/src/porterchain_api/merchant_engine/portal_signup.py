"""Merchant portal first-run seat + company create — owned by merchant_engine."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.email_identity import normalize_email
from porterchain_api.auth.user_sync_service import _is_pending_clerk_id
from porterchain_api.domain.merchant_states import PORTAL_OPEN_STATUSES, MerchantRole
from porterchain_api.merchant_engine.activation_service import (
    SIGNUP_SOURCE_PORTAL,
    apply_signup_policy,
    resolve_initial_status,
)
from porterchain_api.merchant_engine.lookups import (
    get_merchant,
    get_merchant_by_email,
    get_merchant_user_by_email,
    seats_for_clerk,
)
from porterchain_api.merchant_engine.provision import create_onboarding_merchant
from porterchain_api.merchant_engine.team_service import (
    bind_seat_clerk,
    ensure_merchant_seat,
)
from porterchain_api.merchant_models import Merchant, MerchantUser


def claim_pending_seats_for_clerk(db: Session, *, email: str, clerk_id: str) -> int:
    """Bind every reserved ``pending:{email}`` seat to this Clerk user.

    Admin can reserve Owner on company A while the same person already has a linked
    seat on auto-provisioned company B. Without this, later logins resolve via
    ``seats_for_clerk`` → B and never claim A's pending seat — Admin 360 stays
    ``Clerk off`` forever even though OTP login succeeded.
    """
    normalized = normalize_email(email)
    if not normalized or not clerk_id or _is_pending_clerk_id(clerk_id):
        return 0
    claimed = 0
    for seat in db.query(MerchantUser).filter(MerchantUser.email == normalized).all():
        if not _is_pending_clerk_id(seat.clerk_user_id):
            continue
        if seat.clerk_user_id == clerk_id:
            continue
        clash = (
            db.query(MerchantUser)
            .filter(
                MerchantUser.merchant_id == seat.merchant_id,
                MerchantUser.clerk_user_id == clerk_id,
                MerchantUser.id != seat.id,
            )
            .first()
        )
        if clash:
            continue
        bind_seat_clerk(db, seat.id, clerk_id)
        claimed += 1
    return claimed


def resolve_seat(
    db: Session,
    *,
    clerk_id: str,
    email: str,
) -> tuple[MerchantUser | None, Merchant | None]:
    merchant_user: MerchantUser | None = None
    if clerk_id and not _is_pending_clerk_id(clerk_id):
        seats = seats_for_clerk(db, clerk_id)
        merchant_user = seats[0] if seats else None
    if not merchant_user and email:
        merchant_user = get_merchant_user_by_email(db, normalize_email(email) or email)
    merchant: Merchant | None = None
    if merchant_user:
        merchant = get_merchant(db, merchant_user.merchant_id)
    return merchant_user, merchant


def link_or_create_portal_merchant(
    db: Session,
    *,
    email: str,
    clerk_id: str,
    company_name: str,
) -> None:
    """Create merchants + owner seat on first portal sign-in, or bind a reserved seat."""
    email = normalize_email(email) or email
    merchant_user: MerchantUser | None = None
    if clerk_id and not _is_pending_clerk_id(clerk_id):
        seats = seats_for_clerk(db, clerk_id)
        merchant_user = seats[0] if seats else None
    if not merchant_user:
        merchant_user = get_merchant_user_by_email(db, email)

    if merchant_user:
        changed = False
        if clerk_id and not _is_pending_clerk_id(clerk_id) and merchant_user.clerk_user_id != clerk_id:
            if _is_pending_clerk_id(merchant_user.clerk_user_id):
                bind_seat_clerk(db, merchant_user.id, clerk_id)
                changed = True
        # Always heal other reserved seats for this email (Kaylulu Owner, etc.).
        if claim_pending_seats_for_clerk(db, email=email, clerk_id=clerk_id):
            changed = True
        merchant = get_merchant(db, merchant_user.merchant_id)
        if merchant:
            before = merchant.status
            apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_PORTAL)
            changed = changed or merchant.status != before
        if changed:
            db.commit()
        return

    merchant = get_merchant_by_email(db, email)
    if not merchant:
        merchant = create_onboarding_merchant(
            db,
            company_name=company_name,
            email=email,
            status=resolve_initial_status(db, source=SIGNUP_SOURCE_PORTAL),
            profile={"source": SIGNUP_SOURCE_PORTAL, "auto_provisioned": True},
        )
    else:
        apply_signup_policy(db, merchant, source=SIGNUP_SOURCE_PORTAL)

    clerk_ref = clerk_id if clerk_id and not _is_pending_clerk_id(clerk_id) else f"pending:{email}"
    user = ensure_merchant_seat(
        db,
        merchant_id=merchant.id,
        email=email,
        role=MerchantRole.OWNER.value,
        audit_action="merchant.portal_signup_seat",
        commit=False,
    )
    if user.clerk_user_id != clerk_ref:
        bind_seat_clerk(db, user.id, clerk_ref, activate=True)
    claim_pending_seats_for_clerk(db, email=email, clerk_id=clerk_id)
    db.commit()


def save_vertical(db: Session, merchant: Any, vertical: str, industry: str | None) -> None:
    profile = dict(merchant.profile or {})
    profile["vertical"] = vertical
    profile.pop("industry", None)
    merchant.profile = profile
    merchant.industry = industry
    db.commit()


def first_open_seat(db: Session, clerk_user_id: str) -> MerchantUser | None:
    for seat in seats_for_clerk(db, clerk_user_id):
        if not seat.is_active:
            continue
        merchant = get_merchant(db, seat.merchant_id)
        if merchant and merchant.status in PORTAL_OPEN_STATUSES:
            return seat
    seats = [s for s in seats_for_clerk(db, clerk_user_id) if s.is_active]
    return seats[0] if seats else None
