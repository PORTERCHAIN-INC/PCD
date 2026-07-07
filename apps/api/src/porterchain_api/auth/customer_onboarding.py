"""Customer portal onboarding gate."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.user_sync_service import _is_pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.merchant_models import MerchantUser
from porterchain_api.models import Customer


def _identity_conflict_portal(db: Session, clerk_user_id: str) -> str | None:
    if not clerk_user_id or _is_pending_clerk_id(clerk_user_id):
        return None
    if db.query(AdminUser.id).filter(AdminUser.clerk_user_id == clerk_user_id).first():
        return "admin"
    if db.query(MerchantUser.id).filter(MerchantUser.clerk_user_id == clerk_user_id).first():
        return "merchant"
    if db.query(Driver.id).filter(Driver.clerk_user_id == clerk_user_id).first():
        return "driver"
    return None


def evaluate_customer_onboarding(
    db: Session,
    claims: ClerkClaims,
    *,
    settings: Settings | None = None,
    customer: Customer | None = None,
    email: str | None = None,
) -> dict[str, Any]:
    clerk_linked = not _is_pending_clerk_id(claims.clerk_user_id)
    if settings and allow_auth_dev_bypass(settings):
        clerk_linked = True

    if customer is None and claims.clerk_user_id:
        customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()

    email_ok = bool(email or (customer and customer.email))
    conflict = _identity_conflict_portal(db, claims.clerk_user_id or "")
    provisioned = customer is not None

    steps: list[dict[str, Any]] = [
        {
            "id": "clerk_account",
            "label": "Clerk account connected",
            "description": "Sign in with your Porterchain customer account.",
            "complete": clerk_linked,
            "status": "complete" if clerk_linked else "pending",
        },
        {
            "id": "email_on_account",
            "label": "Email on account",
            "description": "A verified email is required for orders, invoices, and support.",
            "complete": email_ok,
            "status": "complete" if email_ok else "pending",
        },
        {
            "id": "customer_provisioned",
            "label": "Customer profile provisioned",
            "description": "Your Porterchain customer record is created and linked to this sign-in.",
            "complete": provisioned,
            "status": "complete" if provisioned else "pending",
        },
        {
            "id": "identity_authorized",
            "label": "Customer identity authorized",
            "description": "This Clerk account must not be provisioned as staff, merchant, or driver.",
            "complete": conflict is None,
            "status": "complete" if conflict is None else f"conflict_{conflict}",
        },
    ]

    blockers = [s["id"] for s in steps if not s["complete"]]
    ready = len(blockers) == 0

    return {
        "ready": ready,
        "blockers": blockers,
        "status": "active" if ready else "pending",
        "clerk_linked": clerk_linked,
        "steps": steps,
        "pending_documents": 0,
        "can_access_portal": ready,
    }


def require_customer_portal_ready(
    db: Session,
    claims: ClerkClaims,
    customer: Customer,
    *,
    settings: Settings | None = None,
    email: str | None = None,
) -> None:
    snapshot = evaluate_customer_onboarding(
        db, claims, settings=settings, customer=customer, email=email
    )
    if snapshot["ready"]:
        return
    blockers = snapshot.get("blockers") or ["onboarding_incomplete"]
    raise PermissionError(f"customer_onboarding_blocked:{','.join(blockers)}")
