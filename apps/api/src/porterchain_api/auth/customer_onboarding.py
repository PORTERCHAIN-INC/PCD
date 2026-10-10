"""Customer portal onboarding gate."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.persona_bundle import load_persona_bundle
from porterchain_api.auth.portal_guard import clerk_id_staff_portal
from porterchain_api.auth.user_sync_service import _is_pending_clerk_id
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings


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
        customer = load_persona_bundle(db, claims.clerk_user_id).customer

    email_ok = bool(email or (customer and customer.email))
    conflict = clerk_id_staff_portal(db, claims.clerk_user_id or "")
    provisioned = customer is not None

    from porterchain_api.admin_engine.platform_settings import (
        portal_enabled as customer_portal_enabled,
    )

    portal_on = customer_portal_enabled(db)

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
        {
            "id": "portal_enabled",
            "label": "Customer portal enabled",
            "description": "Platform settings allow customer portal access.",
            "complete": portal_on,
            "status": "complete" if portal_on else "disabled",
        },
    ]

    blockers = [s["id"] for s in steps if not s["complete"]]
    ready = len(blockers) == 0

    return {
        "ready": ready,
        "blockers": blockers,
        "status": "active" if ready else ("disabled" if not portal_on else "pending"),
        "clerk_linked": clerk_linked,
        "steps": steps,
        "pending_documents": 0,
        "can_access_portal": ready,
        "portal_enabled": portal_on,
    }


def customer_onboarding_payload(db: Session, claims: ClerkClaims, settings: Settings) -> dict[str, Any]:
    from porterchain_api.auth.customer import resolve_customer_contact

    email, _phone = resolve_customer_contact(db, claims, settings)
    customer = provision_customer_for_onboarding(db, claims, settings)
    return evaluate_customer_onboarding(
        db, claims, settings=settings, customer=customer, email=email
    )


def provision_customer_for_onboarding(
    db: Session,
    claims: ClerkClaims,
    settings: Settings,
) -> Customer | None:
    """Create/link the customers row when this Clerk id is allowed on the customer portal."""
    from fastapi import HTTPException

    from porterchain_api.auth.customer import require_customer

    if not claims.clerk_user_id or clerk_id_staff_portal(db, claims.clerk_user_id):
        return None
    try:
        customer = require_customer(db, claims, settings)
        db.commit()
        return customer
    except HTTPException:
        return None


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
