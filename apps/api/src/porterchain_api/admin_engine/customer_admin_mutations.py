"""Admin customer create / invite mutations (kept out of CustomerAdminService LOC budget)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.merchant_lifecycle import ensure_retail_customer
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.identity_directory import directory_for_kind, is_directory_configured
from porterchain_api.auth.email_identity import normalize_email
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings


def _identity_linked(auth_subject: str | None) -> bool:
    if not auth_subject:
        return False
    return not str(auth_subject).startswith("pending")


def create_customer(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    *,
    email: str,
    phone: str | None = None,
    full_name: str | None = None,
    send_invite: bool = False,
) -> dict[str, Any]:
    """Mint a retail customer row for Admin phone-book / care. Optional Keycloak invite."""
    from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService

    normalized = normalize_email(email)
    if not normalized:
        raise ValueError("email_required")

    existing = (
        db.query(Customer)
        .filter(func.lower(Customer.email) == normalized)
        .order_by(Customer.created_at.asc())
        .first()
    )
    if existing and _identity_linked(existing.auth_subject):
        raise ValueError("customer_email_exists")

    created = existing is None
    customer = ensure_retail_customer(
        db,
        email=normalized,
        phone=(phone or "").strip() or None,
        full_name=(full_name or "").strip() or None,
    )
    if full_name and full_name.strip():
        customer.full_name = full_name.strip()[:255]
    if phone and phone.strip():
        customer.phone = phone.strip()[:32]

    identity_action = "created" if created else "reused"
    if send_invite:
        if not is_directory_configured(settings, "customer"):
            raise ValueError("identity_not_configured")
        from porterchain_api.auth.invitation_service import InvitationService

        inv = InvitationService().invite_customer(db, ctx, settings, customer)
        identity_action = str((inv.invitation_metadata or {}).get("identity_action") or "invited")
    elif is_directory_configured(settings, "customer"):
        keycloak = directory_for_kind(settings, "customer")
        found = keycloak.find_user_by_email(normalized)
        if found:
            subject_ref = str(found["id"])
            customer.auth_subject = subject_ref
            keycloak.update_user_metadata(
                subject_ref,
                {
                    "role": "customer",
                    "porterchain_role": "customer",
                    "user_type": "customer",
                    "customer_id": customer.id,
                },
            )
            from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

            sync_authz_after_persona_mutation(db, subject_ref)
            identity_action = "linked_existing_idp"

    log_admin_audit(
        db,
        ctx,
        action="customer.created" if created else "customer.create_reused",
        resource_type="customer",
        resource_id=customer.id,
        payload={
            "email": normalized,
            "send_invite": send_invite,
            "identity_action": identity_action,
        },
    )
    db.commit()
    db.refresh(customer)
    row = CustomerAdminService().detail(db, customer.id)
    row["identity_action"] = identity_action
    row["created"] = created
    return row


def send_invite(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    customer_id: str,
) -> dict[str, Any]:
    """Send or re-send Platform Keycloak invite for an existing customer."""
    from porterchain_api.admin_engine.customer_admin_service import CustomerAdminService

    customer = db.get(Customer, customer_id)
    if not customer:
        raise LookupError("customer_not_found")
    if customer.privacy_status == "deletion_hold":
        raise ValueError("customer_privacy_hold")
    if _identity_linked(customer.auth_subject):
        raise ValueError("customer_already_idp_linked")
    if not is_directory_configured(settings, "customer"):
        raise ValueError("identity_not_configured")
    if not (customer.email or "").strip():
        raise ValueError("email_required")

    from porterchain_api.auth.invitation_service import InvitationService

    inv = InvitationService().invite_customer(db, ctx, settings, customer)
    identity_action = str((inv.invitation_metadata or {}).get("identity_action") or "invited")
    db.commit()
    db.refresh(customer)
    row = CustomerAdminService().detail(db, customer.id)
    row["identity_action"] = identity_action
    return row
