"""Local / re-invite helpers for ClerkDirectoryService (keeps service under ENG-G2 LOC)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService, pending_clerk_id
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import DriverStatus


def _clerk_linked(clerk_user_id: str | None) -> bool:
    if not clerk_user_id:
        return False
    s = str(clerk_user_id)
    return not (s.startswith("pending:") or s.startswith("staff:") or s.startswith("impersonation:"))


_CLERK_DIRECTORY_TYPES = frozenset({"driver", "customer", "merchant"})


def invite_directory_user(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    user_type: str,
    *,
    platform_user_id: str,
) -> dict[str, Any]:
    """Re-send Clerk invite for an existing driver or customer (Settings → Users)."""
    if user_type not in _CLERK_DIRECTORY_TYPES:
        raise ValueError("invalid_user_type")
    if user_type == "merchant":
        raise ValueError("merchant_seats_bind_on_signin_not_invite")
    if user_type == "driver":
        if not is_clerk_secret_configured(settings, "driver"):
            raise ValueError("clerk_not_configured")
        driver = db.query(Driver).filter(Driver.id == platform_user_id).first()
        if not driver:
            raise LookupError("driver_not_found")
        return InvitationService().invite_existing_driver(db, ctx, settings, driver)
    if user_type == "customer":
        from porterchain_api.admin_engine.customer_admin_mutations import send_invite

        return send_invite(db, ctx, settings, platform_user_id)
    raise ValueError(f"invite_unsupported_for_{user_type}")


def create_local_driver(
    db: Session,
    ctx: AdminContext,
    *,
    email: str,
    name: str | None,
) -> dict[str, Any]:
    """PENDING driver row without Clerk — Super Admin can approve / assign before portal login."""
    existing = db.query(Driver).filter(Driver.email == email).first()
    if existing:
        return {
            "platform_user_id": existing.id,
            "clerk_user_id": existing.clerk_user_id if _clerk_linked(existing.clerk_user_id) else None,
            "clerk_action": "reused_local",
            "email": email,
        }
    driver = Driver(
        full_name=name or email.split("@")[0],
        email=email,
        clerk_user_id=pending_clerk_id(email),
        status=DriverStatus.PENDING.value,
    )
    db.add(driver)
    db.flush()
    log_admin_audit(
        db,
        ctx,
        action="settings.user.created",
        resource_type="driver",
        resource_id=driver.id,
        payload={"email": email, "clerk_action": "local_pending"},
    )
    db.commit()
    return {
        "platform_user_id": driver.id,
        "clerk_user_id": None,
        "clerk_action": "local_pending",
        "email": email,
    }
