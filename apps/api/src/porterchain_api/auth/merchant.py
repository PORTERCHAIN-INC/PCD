"""Resolve merchant context from Clerk JWT + Porterchain merchant_users (no Clerk Organizations)."""

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.dev import (
    allow_auth_dev_bypass,
    is_dev_bypass_subject,
    is_merchant_dev_subject,
)
from porterchain_api.auth.email_identity import (
    CLERK_EMAIL_REQUIRED,
    CLERK_EMAIL_UNVERIFIED,
    EMAIL_CLERK_MISMATCH,
    assert_portal_email_identity,
    normalize_email,
)
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import PORTAL_OPEN_STATUSES, MerchantStatus
from porterchain_api.merchant_engine.lookups import get_merchant, seats_for_clerk
from porterchain_api.merchant_engine.portal_signup import (
    claim_pending_seats_for_clerk,
    first_open_seat,
)
from porterchain_api.merchant_engine.provision import ensure_dev_merchant_seat
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role


@dataclass
class DevMerchantHeaders:
    merchant_id: str | None = None
    role: str | None = None


@dataclass
class MerchantSeats:
    """Every seat this Clerk user holds, whatever each company's status is (BF)."""

    clerk_user_id: str
    seats: list[Any]
    selected_merchant_id: str | None = None


def portal_access_denied(merchant: Any) -> str | None:
    """English-stable 403 codes for the merchant portal gate."""
    if merchant.status == MerchantStatus.CLOSED.value:
        return "merchant_closed"
    if merchant.status == MerchantStatus.SUSPENDED.value:
        return "merchant_suspended"
    if merchant.status not in PORTAL_OPEN_STATUSES:
        return "merchant_not_active"
    return None


def get_merchant_context(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_merchant_id: Annotated[str | None, Header()] = None,
) -> MerchantContext:
    """
    Authorization uses Porterchain merchant_users only.

    Optional X-Merchant-Id selects membership when a user belongs to multiple merchants.
    Role is always taken from merchant_users.role — never from request headers.
    """
    meta = claims.public_metadata or {}
    if meta.get("impersonation") and meta.get("user_type") == "merchant":
        return _merchant_context_from_impersonation(db, str(meta.get("target_id") or ""))

    assert_clerk_id_exclusive(db, claims, portal="merchant", settings=settings)

    # Heal Admin-reserved pending seats even when AccessGate skips onboarding
    # because another company for this Clerk user is already ACTIVE.
    email = normalize_email(claims.email)
    if email and claim_pending_seats_for_clerk(db, email=email, clerk_id=claims.clerk_user_id):
        db.commit()

    user = _resolve_merchant_user(db, claims.clerk_user_id, x_merchant_id, settings)
    # Local Bearer-dev synthetic subjects have no SpiceDB tuples; email is the portal persona.
    if not is_dev_bypass_subject(claims.clerk_user_id):
        try:
            assert_portal_email_identity(user.email, claims.email)
        except PermissionError as exc:
            detail = str(exc)
            if detail in {CLERK_EMAIL_REQUIRED, CLERK_EMAIL_UNVERIFIED, EMAIL_CLERK_MISMATCH}:
                raise HTTPException(status_code=403, detail=detail) from exc
            raise HTTPException(status_code=403, detail=EMAIL_CLERK_MISMATCH) from exc

    # SpiceDB ReBAC: organization#portal required — fail closed when unprovisioned.
    # Local CLERK_DEV_BYPASS synthetic subject has no SpiceDB tuples by design.
    if not is_dev_bypass_subject(claims.clerk_user_id):
        from porterchain_api.auth.dependencies import (
            assert_organization_scope,
            resolve_principal_for_claims,
        )

        principal = resolve_principal_for_claims(db, claims)
        if not principal:
            raise HTTPException(status_code=403, detail="user_not_provisioned")
        assert_organization_scope(principal, user.merchant_id, db)
        if not user.porterchain_user_id:
            user.porterchain_user_id = principal.user_id

    merchant = get_merchant(db, user.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant_not_found")

    denied = portal_access_denied(merchant)
    if denied:
        raise HTTPException(status_code=403, detail=denied)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="merchant_user_inactive")

    role = parse_merchant_role(user.role)
    return MerchantContext(merchant=merchant, user=user, role=role)


def _merchant_context_from_impersonation(db: Session, merchant_user_id: str) -> MerchantContext:
    from porterchain_api.merchant_engine.lookups import get_merchant_user

    if not merchant_user_id:
        raise HTTPException(status_code=401, detail="impersonation_expired")
    user = get_merchant_user(db, merchant_user_id)
    if not user:
        raise HTTPException(status_code=404, detail="merchant_user_not_found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="merchant_user_inactive")
    merchant = get_merchant(db, user.merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant_not_found")
    denied = portal_access_denied(merchant)
    if denied:
        raise HTTPException(status_code=403, detail=denied)
    role = parse_merchant_role(user.role)
    return MerchantContext(merchant=merchant, user=user, role=role)


def get_merchant_seats(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_merchant_id: Annotated[str | None, Header()] = None,
) -> MerchantSeats:
    """Seat list for the company switcher — no company-status gate (BF).

    ``get_merchant_context`` rejects suspended and closed companies (AZ), which
    would hide the switcher exactly when someone needs it to move to a company
    that still works. Identity checks stay; only the status gate is dropped.
    """
    meta = claims.public_metadata or {}
    if meta.get("impersonation") and meta.get("user_type") == "merchant":
        from porterchain_api.merchant_engine.lookups import get_merchant_user

        mu = get_merchant_user(db, str(meta.get("target_id") or ""))
        if not mu or not mu.is_active:
            raise HTTPException(status_code=403, detail="merchant_user_not_found")
        return MerchantSeats(
            clerk_user_id=claims.clerk_user_id,
            seats=[mu],
            selected_merchant_id=mu.merchant_id,
        )

    assert_clerk_id_exclusive(db, claims, portal="merchant", settings=settings)

    seats = [s for s in seats_for_clerk(db, claims.clerk_user_id) if s.is_active]
    if not seats and allow_auth_dev_bypass(settings) and is_merchant_dev_subject(claims.clerk_user_id):
        seats = [ensure_dev_merchant_seat(db, claims.clerk_user_id)]
    if not seats:
        raise HTTPException(status_code=403, detail="merchant_user_not_found")

    if not is_dev_bypass_subject(claims.clerk_user_id):
        try:
            assert_portal_email_identity(seats[0].email, claims.email)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=EMAIL_CLERK_MISMATCH) from exc

    requested = (x_merchant_id or "").strip() or None
    if requested and not any(seat.merchant_id == requested for seat in seats):
        raise HTTPException(status_code=403, detail="merchant_membership_not_found")

    return MerchantSeats(
        clerk_user_id=claims.clerk_user_id,
        seats=seats,
        selected_merchant_id=requested,
    )


def _resolve_merchant_user(
    db: Session,
    clerk_user_id: str,
    merchant_id: str | None,
    settings: Settings,
) -> Any:
    if merchant_id:
        seats = [s for s in seats_for_clerk(db, clerk_user_id) if s.merchant_id == merchant_id]
        if seats:
            return seats[0]
        # Browser kept pc_merchant_id from a previous sign-in. Do not treat that
        # as "this owner withheld Overview" — open the company this user belongs to.
    user = first_open_seat(db, clerk_user_id)
    if user:
        return user

    if allow_auth_dev_bypass(settings) and is_merchant_dev_subject(clerk_user_id):
        return ensure_dev_merchant_seat(db, clerk_user_id)

    raise HTTPException(status_code=403, detail="merchant_user_not_found")
