"""Merchant account ops for Admin: health v2, credit hold, connections watchdog,
quote preview + margin floor, documents, board / segments / bulk.

Merchant-domain logic lives here (merchant_engine). Billing numbers come through
``merchant_engine.billing_views``; role gates and staff identity are passed in by
the admin router, so this package never imports admin_engine.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.merchant_models import Merchant, MerchantAuditLog


def get_merchant(db: Session, merchant_id: str) -> Merchant:
    merchant = db.get(Merchant, merchant_id)
    if merchant is None:
        raise LookupError("merchant_not_found")
    return merchant


def staff_audit(
    db: Session,
    ctx: Any,
    merchant_id: str,
    *,
    action: str,
    resource_type: str,
    resource_id: str | None,
    payload: dict | None = None,
    commit: bool = True,
) -> None:
    """Same row shape as admin ``write_staff_audit`` (actor admin:<id>, role + email in payload)."""
    role = getattr(ctx, "role", None)
    body = {
        "admin_user_id": getattr(ctx.user, "id", None),
        "admin_email": getattr(ctx.user, "email", None),
        "admin_role": getattr(role, "value", role),
        **(payload or {}),
    }
    db.add(
        MerchantAuditLog(
            merchant_id=merchant_id,
            actor_user_id=f"admin:{getattr(ctx.user, 'id', None)}",
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=body,
        )
    )
    if commit:
        db.commit()
    else:
        db.flush()
