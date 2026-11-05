"""Admin customer convert-to-merchant — keep order history on the customer row."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.booking_models import Customer
from porterchain_api.config import Settings
from porterchain_api.domain.merchant_states import MerchantRole
from porterchain_api.merchant_models import Merchant


def _identity_linked(auth_subject: str | None) -> bool:
    if not auth_subject:
        return False
    value = str(auth_subject)
    return not value.startswith("pending") and not value.startswith("converted:")


def _find_converted_merchant(db: Session, customer_id: str) -> Merchant | None:
    # profile JSON key set at convert time; scan recent merchants (admin-scale).
    rows = db.query(Merchant).order_by(Merchant.created_at.desc()).limit(500).all()
    for merchant in rows:
        profile = merchant.profile or {}
        if profile.get("converted_from_customer_id") == customer_id:
            return merchant
    return None


def convert_to_merchant(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    customer_id: str,
    *,
    company_name: str | None = None,
    auto_activate: bool = True,
    send_invite: bool = False,
) -> dict[str, Any]:
    """Create a merchant from a retail customer. Orders stay on the customer id."""
    from porterchain_api.admin_engine.audit import log_admin_audit
    from porterchain_api.admin_engine.merchant_service import AdminMerchantService
    from porterchain_api.auth.identity_directory import directory_for_kind, is_directory_configured
    from porterchain_api.merchant_engine.lifecycle import merge_profile
    from porterchain_api.merchant_engine.lookups import get_merchant_user_by_email, get_seat_by_idp

    customer = db.get(Customer, customer_id)
    if not customer:
        raise LookupError("customer_not_found")

    existing = _find_converted_merchant(db, customer_id)
    if existing:
        return {
            "customer_id": customer_id,
            "merchant_id": existing.id,
            "status": existing.status,
            "company_name": existing.company_name,
            "idempotent": True,
        }

    if customer.deleted_at is not None:
        raise LookupError("customer_not_found")
    if customer.privacy_status == "deletion_hold":
        raise ValueError("customer_privacy_hold")

    email = (customer.email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("email_required")

    name = (company_name or "").strip() or (customer.full_name or "").strip() or email.split("@")[0]
    old_subject = customer.auth_subject

    svc = AdminMerchantService()
    merchant = svc.create_merchant(
        db,
        ctx,
        settings,
        email=email,
        company_name=name,
        auto_activate=auto_activate,
        send_invite=send_invite,
    )
    merge_profile(
        merchant,
        {
            "converted_from_customer_id": customer.id,
            "converted_from_customer_email": email,
            "converted_at": datetime.now(UTC).isoformat(),
            "converted_by": ctx.user.id,
        },
    )

    # When the customer already had a Keycloak subject, bind the owner seat to it
    # even if create_merchant skipped invite/link (send_invite=False).
    if _identity_linked(old_subject):
        conflict = get_seat_by_idp(db, old_subject)
        seat = get_merchant_user_by_email(db, email, merchant_id=merchant.id)
        if conflict is not None and (seat is None or conflict.id != seat.id):
            raise ValueError("merchant_user_email_exists")
        if seat is not None:
            seat.auth_subject = old_subject
            seat.is_active = True
            seat.role = MerchantRole.OWNER.value
        if is_directory_configured(settings, "merchant"):
            keycloak = directory_for_kind(settings, "merchant")
            keycloak.update_user_metadata(
                old_subject,
                {
                    "role": MerchantRole.OWNER.value,
                    "porterchain_role": MerchantRole.OWNER.value,
                    "user_type": "merchant",
                    "merchant_id": merchant.id,
                },
            )

    # Free the Keycloak subject for the merchant seat; keep a unique placeholder on customer.
    customer.auth_subject = f"converted:{customer.id}:{merchant.id}"[:128]
    customer.deleted_at = datetime.now(UTC)
    customer.deleted_by = ctx.user.id
    customer.delete_reason = "converted_to_merchant"

    log_admin_audit(
        db,
        ctx,
        action="customer.converted_to_merchant",
        resource_type="customer",
        resource_id=customer.id,
        payload={
            "merchant_id": merchant.id,
            "email": email,
            "prior_auth_subject": old_subject,
            "identity_linked": _identity_linked(old_subject),
            "auto_activate": auto_activate,
            "send_invite": send_invite,
        },
    )
    db.commit()
    db.refresh(merchant)
    return {
        "customer_id": customer.id,
        "merchant_id": merchant.id,
        "status": merchant.status,
        "company_name": merchant.company_name,
        "idempotent": False,
    }


__all__ = ["convert_to_merchant"]
