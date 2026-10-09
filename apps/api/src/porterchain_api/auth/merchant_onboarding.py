"""Merchant portal onboarding gate."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.auth.user_sync_service import UserSyncService, _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantStatus
from porterchain_api.domain.catalog_labels import onboarding_step_status_label
from porterchain_api.merchant_engine.company_file import (
    can_edit_company_file,
    company_file_missing,
    company_file_snapshot,
    completeness_payload,
    merchant_status_label,
    signup_url,
)
from porterchain_api.merchant_engine.organization_sync import branding_logo_url
from porterchain_api.merchant_engine.rbac import MerchantContext, english_role, parse_merchant_role
from porterchain_api.merchant_engine.verticals import (
    MERCHANT_VERTICAL_SLUGS,
    VERTICAL_INDUSTRY,
    VERTICAL_LABELS,
    is_valid_merchant_vertical,
)
from porterchain_api.merchant_engine.portal_signup import (
    link_or_create_portal_merchant,
    resolve_seat,
    save_vertical,
)
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest

logger = logging.getLogger(__name__)


def resolve_merchant_contact(
    db: Session,
    claims: ClerkClaims,
    settings: Settings | None,
) -> str | None:
    """Resolve Clerk-attested email only (JWT or verified Backend primary). Never DB."""
    _ = db
    from porterchain_api.auth.email_identity import normalize_email, resolve_verified_clerk_email

    email = normalize_email(claims.email)
    if email:
        return email

    clerk_id = claims.clerk_user_id or ""
    if not clerk_id or _is_pending_clerk_id(clerk_id) or not settings:
        return None
    try:
        return resolve_verified_clerk_email(
            jwt_email=None,
            clerk_user_id=clerk_id,
            settings=settings,
        )
    except PermissionError:
        logger.warning("merchant_email_clerk_lookup_failed", exc_info=False)
        return None


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
    lists them immediately. Starting status comes from the activation policy —
    ONBOARDING while `settings_merchant.approval_required` is on.
    """
    email = resolve_merchant_contact(db, claims, settings) or ""
    clerk_id = claims.clerk_user_id or ""
    if not email:
        raise HTTPException(status_code=400, detail="email_required")

    if clerk_id and not _is_pending_clerk_id(clerk_id):
        bundle = load_persona_bundle(db, clerk_id)
        if bundle.admin is not None:
            raise HTTPException(status_code=403, detail="identity_conflict:clerk_user_is_admin")
        if bundle.driver is not None:
            raise HTTPException(status_code=403, detail="identity_conflict:clerk_user_is_driver")

    link_or_create_portal_merchant(
        db,
        email=email,
        clerk_id=clerk_id,
        company_name=_derive_company_name(claims, email),
    )
    if clerk_id:
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, clerk_id)

    try:
        UserSyncService().sync(db, claims)
    except Exception:
        logger.warning("merchant_portal_user_sync_failed", exc_info=True)


def _resolve_seat(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> tuple[Any, Any]:
    email = resolve_merchant_contact(db, claims, settings) or ""
    clerk_id = claims.clerk_user_id or ""
    return resolve_seat(db, clerk_id=clerk_id, email=email)


def evaluate_merchant_onboarding(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    if settings and not allow_auth_dev_bypass(settings):
        ensure_merchant_portal_signup(db, claims, settings=settings)

    clerk_id = claims.clerk_user_id or ""
    merchant_user, merchant = _resolve_seat(db, claims, settings=settings)

    clerk_linked = not _is_pending_clerk_id(clerk_id)
    if settings and allow_auth_dev_bypass(settings):
        clerk_linked = True

    invited = merchant_user is not None
    user_active = bool(merchant_user and merchant_user.is_active)
    merchant_status = merchant.status if merchant else MerchantStatus.PENDING.value
    admin_approved = merchant_status == MerchantStatus.ACTIVE.value
    role = parse_merchant_role(merchant_user.role) if merchant_user else None
    file_missing = company_file_missing(merchant)
    file_complete = bool(merchant) and not file_missing
    vertical_slug = (merchant.profile or {}).get("vertical") if merchant else None
    vertical_ready = bool(vertical_slug and is_valid_merchant_vertical(str(vertical_slug)))
    edit_company = can_edit_company_file(merchant_status, role) if role else False

    activation_status = (
        "complete"
        if admin_approved
        else "suspended"
        if merchant_status == MerchantStatus.SUSPENDED.value
        else "onboarding"
        if merchant_status == MerchantStatus.ONBOARDING.value
        else "closed"
        if merchant_status == MerchantStatus.CLOSED.value
        else "pending"
    )

    steps: list[dict[str, Any]] = [
        {
            "id": "clerk_account",
            "label": "Signed in",
            "description": "You signed in at the merchant portal. Password and MFA stay in your Clerk account.",
            "complete": clerk_linked,
            "status": "complete" if clerk_linked else "pending",
        },
        {
            "id": "merchant_provisioned",
            "label": "Company seat",
            "description": "This email has a seat on a PorterChain company.",
            "complete": invited,
            "status": "complete" if invited else "pending",
        },
        {
            "id": "company_profile",
            "label": "Company file",
            "description": (
                "Owners add legal name, phone, billing address, and HST. "
                "Dispatchers can use the portal without HST."
            ),
            "complete": file_complete,
            "status": "complete" if file_complete else "pending",
            "missing": file_missing,
        },
        {
            "id": "business_vertical",
            "label": "Business type",
            "description": "Optional. Helps PorterChain tailor booking fields. Does not lock the portal.",
            "complete": vertical_ready,
            "status": "complete" if vertical_ready else "pending",
        },
        {
            "id": "admin_authorization",
            "label": merchant_status_label(merchant_status),
            "description": (
                "PorterChain activates the company before bookings. "
                "You can finish the company file while status is Onboarding."
            ),
            "complete": admin_approved,
            "status": activation_status,
        },
        {
            "id": "team_access",
            "label": "Your seat is on",
            "description": (
                "Your owner turned this seat on."
                if user_active
                else "Your owner turned this seat off. Ask them to turn it back on."
            ),
            "complete": user_active,
            "status": "complete" if user_active else "inactive",
        },
    ]
    for step in steps:
        step["status_label"] = onboarding_step_status_label(
            step.get("status"),
            complete=bool(step.get("complete")),
        )

    blockers: list[str] = []
    if not clerk_linked:
        blockers.append("clerk_account")
    if not invited:
        blockers.append("merchant_provisioned")
    if invited and not user_active:
        blockers.append("team_access")
    if merchant_status == MerchantStatus.SUSPENDED.value:
        blockers.append("account_suspended")
    elif merchant_status == MerchantStatus.CLOSED.value:
        blockers.append("merchant_closed")
    elif merchant_status != MerchantStatus.ACTIVE.value:
        blockers.append("admin_authorization")

    ready = len(blockers) == 0

    return {
        "ready": ready,
        "blockers": blockers,
        "status": merchant_status,
        "status_label": merchant_status_label(merchant_status),
        "clerk_linked": clerk_linked,
        "steps": steps,
        "pending_documents": 0,
        "can_access_portal": ready,
        "company_name": merchant.company_name if merchant else None,
        "merchant_id": merchant.id if merchant else None,
        "role": role.value if role else None,
        "role_label": english_role(role) if role else None,
        "can_edit_company": edit_company,
        "completeness": completeness_payload(merchant, can_edit=edit_company),
        "company_file": company_file_snapshot(merchant),
        "signup_url": signup_url(settings.merchant_portal_url if settings else None),
        "logo_url": branding_logo_url(merchant) if merchant else None,
        "vertical": str(vertical_slug) if vertical_slug else None,
        "vertical_label": VERTICAL_LABELS.get(str(vertical_slug), None) if vertical_slug else None,
        "vertical_options": [
            {"slug": slug, "label": VERTICAL_LABELS[slug]} for slug in MERCHANT_VERTICAL_SLUGS
        ],
    }


def _require_seat(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
) -> tuple[Any, Any]:
    if settings:
        ensure_merchant_portal_signup(db, claims, settings=settings)
    merchant_user, merchant = _resolve_seat(db, claims, settings=settings)
    if not merchant_user or not merchant:
        raise HTTPException(status_code=404, detail="That company was not found.")
    return merchant_user, merchant


def save_merchant_vertical(
    db: Session,
    claims: ClerkClaims,
    vertical: str,
    *,
    settings: Settings | None = None,
    attribution: dict[str, str] | None = None,
) -> dict[str, Any]:
    if not is_valid_merchant_vertical(vertical):
        raise HTTPException(status_code=400, detail="Pick a business type from the list.")

    merchant_user, merchant = _require_seat(db, claims, settings=settings)
    if not can_edit_company_file(merchant.status, merchant_user.role):
        raise HTTPException(
            status_code=403,
            detail="Ask your owner to finish the company file.",
        )

    if attribution:
        from porterchain_api.marketing_site.signup_attribution import stamp_signup_attribution

        stamp_signup_attribution(merchant, attribution)
    save_vertical(db, merchant, vertical, VERTICAL_INDUSTRY.get(vertical))

    return evaluate_merchant_onboarding(db, claims, settings=settings)


def save_merchant_company_file(
    db: Session,
    claims: ClerkClaims,
    body: MerchantProfileUpdateRequest,
    *,
    settings: Settings | None = None,
) -> dict[str, Any]:
    merchant_user, merchant = _require_seat(db, claims, settings=settings)
    if not can_edit_company_file(merchant.status, merchant_user.role):
        raise HTTPException(
            status_code=403,
            detail="Ask your owner to finish the company file.",
        )

    from porterchain_api.merchant_engine.profile_service import MerchantProfileService

    ctx = MerchantContext(
        merchant=merchant,
        user=merchant_user,
        role=parse_merchant_role(merchant_user.role),
    )
    try:
        MerchantProfileService().update_profile(db, ctx, body)
    except ValueError as exc:
        if str(exc) == "email_invalid":
            raise HTTPException(status_code=400, detail="Enter a valid company email.") from exc
        raise HTTPException(status_code=400, detail="That company file could not be saved.") from exc

    return evaluate_merchant_onboarding(db, claims, settings=settings)
