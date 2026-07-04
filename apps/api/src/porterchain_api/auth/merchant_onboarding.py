"""Merchant portal onboarding gate."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.portal_guard import require_clerk_app_for_portal
from porterchain_api.auth.user_sync_service import UserSyncService, _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_models import Merchant, MerchantUser
from porterchain_api.admin_models import AdminUser, Driver

logger = logging.getLogger(__name__)


def _derive_company_name(claims: ClerkClaims, email: str) -> str:
    meta = claims.public_metadata or {}
    if meta.get("company_name"):
        return str(meta["company_name"]).strip()
    local = email.split("@")[0]
    name = local.replace(".", " ").replace("_", " ").strip()
    return name.title() if name else "Merchant"


def ensure_merchant_portal_signup(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> None:
    """
    Any authenticated merchant-portal Clerk session is a merchant candidate.

    First sign-in at :3001 creates merchants + merchant_users so admin /merchants
    lists them immediately (status ONBOARDING until ops approves).
    """
    if settings:
        require_clerk_app_for_portal(claims, settings, "merchant")

    email = (claims.email or "").lower().strip()
    clerk_id = claims.clerk_user_id or ""
    if not email:
        raise HTTPException(status_code=400, detail="email_required")

    if clerk_id and not _is_pending_clerk_id(clerk_id):
        if db.query(AdminUser.id).filter(AdminUser.clerk_user_id == clerk_id).first():
            raise HTTPException(status_code=403, detail="identity_conflict:clerk_user_is_admin")
        if db.query(Driver.id).filter(Driver.clerk_user_id == clerk_id).first():
            raise HTTPException(status_code=403, detail="identity_conflict:clerk_user_is_driver")

    merchant_user: MerchantUser | None = None
    if clerk_id and not _is_pending_clerk_id(clerk_id):
        merchant_user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_id).first()
    if not merchant_user:
        merchant_user = db.query(MerchantUser).filter(MerchantUser.email == email).first()

    if merchant_user:
        changed = False
        if clerk_id and not _is_pending_clerk_id(clerk_id) and merchant_user.clerk_user_id != clerk_id:
            if _is_pending_clerk_id(merchant_user.clerk_user_id):
                merchant_user.clerk_user_id = clerk_id
                changed = True
        if not merchant_user.is_active:
            merchant_user.is_active = True
            changed = True
        merchant = db.query(Merchant).filter(Merchant.id == merchant_user.merchant_id).first()
        if merchant and merchant.status == MerchantStatus.PENDING.value:
            merchant.status = MerchantStatus.ONBOARDING.value
            changed = True
        if changed:
            db.commit()
        return

    merchant = db.query(Merchant).filter(Merchant.email == email).order_by(Merchant.created_at.desc()).first()
    if not merchant:
        merchant = Merchant(
            status=MerchantStatus.ONBOARDING.value,
            company_name=_derive_company_name(claims, email),
            email=email,
            payment_terms="NET_30",
            profile={"source": "merchant_portal_signin", "auto_provisioned": True},
        )
        db.add(merchant)
        db.flush()
    elif merchant.status == MerchantStatus.PENDING.value:
        merchant.status = MerchantStatus.ONBOARDING.value

    clerk_ref = clerk_id if clerk_id and not _is_pending_clerk_id(clerk_id) else f"pending:{email}"
    db.add(
        MerchantUser(
            merchant_id=merchant.id,
            clerk_user_id=clerk_ref,
            email=email,
            role=MerchantRole.OWNER.value,
            is_active=True,
        )
    )
    db.commit()

    try:
        UserSyncService().sync(db, claims)
    except Exception:
        logger.warning("merchant_portal_user_sync_failed", exc_info=True)


def evaluate_merchant_onboarding(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    if settings and not allow_auth_dev_bypass(settings):
        ensure_merchant_portal_signup(db, claims, settings=settings)

    email = (claims.email or "").lower().strip()
    clerk_id = claims.clerk_user_id or ""

    merchant_user: MerchantUser | None = None
    if clerk_id and not _is_pending_clerk_id(clerk_id):
        merchant_user = db.query(MerchantUser).filter(MerchantUser.clerk_user_id == clerk_id).first()
    if not merchant_user and email:
        merchant_user = db.query(MerchantUser).filter(MerchantUser.email == email).first()

    merchant: Merchant | None = None
    if merchant_user:
        merchant = db.query(Merchant).filter(Merchant.id == merchant_user.merchant_id).first()

    clerk_linked = not _is_pending_clerk_id(clerk_id)
    if settings and allow_auth_dev_bypass(settings):
        clerk_linked = True

    invited = merchant_user is not None
    user_active = bool(merchant_user and merchant_user.is_active)
    merchant_status = merchant.status if merchant else MerchantStatus.PENDING.value
    admin_approved = merchant_status == MerchantStatus.ACTIVE.value
    company_ready = bool(merchant and merchant.company_name and merchant.email)

    steps: list[dict[str, Any]] = [
        {
            "id": "clerk_account",
            "label": "Merchant portal sign-in",
            "description": "Sign in at the Porterchain merchant portal with your business email.",
            "complete": clerk_linked,
            "status": "complete" if clerk_linked else "pending",
        },
        {
            "id": "merchant_provisioned",
            "label": "Merchant account provisioned",
            "description": "Your account is registered as a Porterchain merchant organization.",
            "complete": invited,
            "status": "complete" if invited else "pending",
        },
        {
            "id": "admin_authorization",
            "label": "Admin authorization",
            "description": "Operations must activate your merchant account before portal access.",
            "complete": admin_approved,
            "status": (
                "complete"
                if admin_approved
                else "suspended"
                if merchant_status == MerchantStatus.SUSPENDED.value
                else "onboarding"
                if merchant_status == MerchantStatus.ONBOARDING.value
                else "pending"
            ),
        },
        {
            "id": "team_access",
            "label": "Team access active",
            "description": "Your merchant user membership must be active.",
            "complete": user_active,
            "status": "complete" if user_active else "inactive",
        },
        {
            "id": "company_profile",
            "label": "Company profile on file",
            "description": "Business name and contact email are registered with Porterchain.",
            "complete": company_ready,
            "status": "complete" if company_ready else "pending",
        },
    ]

    blockers = [s["id"] for s in steps if not s["complete"]]
    ready = len(blockers) == 0

    if merchant_status == MerchantStatus.SUSPENDED.value:
        ready = False
        blockers = ["account_suspended"]
    elif not invited:
        ready = False
        if "merchant_provisioned" not in blockers:
            blockers.insert(0, "merchant_user_not_found")

    return {
        "ready": ready,
        "blockers": blockers,
        "status": merchant_status,
        "clerk_linked": clerk_linked,
        "steps": steps,
        "pending_documents": 0,
        "can_access_portal": ready,
        "company_name": merchant.company_name if merchant else None,
        "merchant_id": merchant.id if merchant else None,
    }
