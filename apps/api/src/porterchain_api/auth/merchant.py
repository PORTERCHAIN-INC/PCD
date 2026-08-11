"""Resolve merchant context from Clerk JWT + Porterchain merchant_users (no Clerk Organizations)."""

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.email_identity import (
    CLERK_EMAIL_REQUIRED,
    CLERK_EMAIL_UNVERIFIED,
    EMAIL_CLERK_MISMATCH,
    assert_portal_email_identity,
)
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_api.merchant_models import Merchant, MerchantUser


@dataclass
class DevMerchantHeaders:
    merchant_id: str | None = None
    role: str | None = None


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
    assert_clerk_id_exclusive(db, claims, portal="merchant", settings=settings)

    user = _resolve_merchant_user(db, claims.clerk_user_id, x_merchant_id, settings)
    # Local CLERK_DEV_BYPASS uses a shared synthetic clerk id; email may not match seed rows.
    if claims.clerk_user_id != "dev_clerk_user":
        try:
            assert_portal_email_identity(user.email, claims.email)
        except PermissionError as exc:
            detail = str(exc)
            if detail in {CLERK_EMAIL_REQUIRED, CLERK_EMAIL_UNVERIFIED, EMAIL_CLERK_MISMATCH}:
                raise HTTPException(status_code=403, detail=detail) from exc
            raise HTTPException(status_code=403, detail=EMAIL_CLERK_MISMATCH) from exc

    # SpiceDB ReBAC: organization#portal required — fail closed when unprovisioned.
    # Local CLERK_DEV_BYPASS synthetic subject has no SpiceDB tuples by design.
    if claims.clerk_user_id != "dev_clerk_user":
        from porterchain_api.auth.dependencies import assert_organization_scope, resolve_principal_for_claims

        principal = resolve_principal_for_claims(db, claims)
        if not principal:
            raise HTTPException(status_code=403, detail="user_not_provisioned")
        assert_organization_scope(principal, user.merchant_id, db)
        if not user.porterchain_user_id:
            user.porterchain_user_id = principal.user_id

    merchant = db.query(Merchant).filter(Merchant.id == user.merchant_id).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="merchant_not_found")

    if merchant.status != MerchantStatus.ACTIVE.value:
        raise HTTPException(status_code=403, detail="merchant_not_active")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="merchant_user_inactive")

    role = parse_merchant_role(user.role)
    return MerchantContext(merchant=merchant, user=user, role=role)


def _resolve_merchant_user(
    db: Session,
    clerk_user_id: str,
    merchant_id: str | None,
    settings: Settings,
) -> MerchantUser:
    query = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id)
    if merchant_id:
        user = query.filter(MerchantUser.merchant_id == merchant_id).first()
        if not user:
            raise HTTPException(status_code=403, detail="merchant_membership_not_found")
        return user

    user = query.filter(MerchantUser.is_active.is_(True)).order_by(MerchantUser.created_at).first()
    if user:
        return user

    if allow_auth_dev_bypass(settings):
        return _ensure_dev_user(db, clerk_user_id)

    raise HTTPException(status_code=403, detail="merchant_user_not_found")


def _ensure_dev_user(db: Session, clerk_user_id: str) -> MerchantUser:
    merchant = db.query(Merchant).filter(Merchant.clerk_org_id == "dev_merchant_org").first()
    if not merchant:
        merchant = Merchant(
            clerk_org_id="dev_merchant_org",
            status=MerchantStatus.ACTIVE.value,
            company_name="Dev Merchant Co.",
            email="merchant@example.com",
            payment_terms="NET_30",
            activated_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
        )
        db.add(merchant)
        db.flush()

    user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_user_id).first()
    if user:
        return user

    user = MerchantUser(
        merchant_id=merchant.id,
        clerk_user_id=clerk_user_id,
        email="admin@porterchain.com",
        role="merchant_owner",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

    sync_authz_after_persona_mutation(db, clerk_user_id)
    return user
