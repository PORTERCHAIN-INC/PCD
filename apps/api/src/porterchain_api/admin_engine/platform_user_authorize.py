"""Authorize platform users for portal access (Settings → Users).

Staff: activate existing AdminUser only via Staff IdP — never promote to
super_admin, never create staff from a Clerk signup (enroll first).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.audit import log_admin_audit
from porterchain_api.admin_engine.clerk_directory_service import require_platform_user_type
from porterchain_api.admin_engine.driver_service import AdminDriverService
from porterchain_api.admin_engine.merchant_service import AdminMerchantService
from porterchain_api.admin_engine.rbac import MODULE_PERMISSIONS, AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser, Driver
from porterchain_api.config import Settings
from porterchain_api.domain.admin_states import AdminRole, DriverStatus
from porterchain_api.domain.merchant_states import MerchantRole, MerchantStatus
from porterchain_api.merchant_engine.rbac import MODULE_PERMISSIONS as MERCHANT_MODULE_PERMISSIONS
from porterchain_api.merchant_engine.lookups import (
    get_merchant,
    get_merchant_by_email,
    get_merchant_user,
    get_merchant_user_by_email,
    seats_for_clerk,
)
from porterchain_api.merchant_engine.provision import create_onboarding_merchant
from porterchain_api.merchant_engine.team_service import bind_seat_clerk, ensure_merchant_seat
from porterchain_api.schemas_admin import PlatformUserAuthorizeResponse


def authorize_platform_user(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    user_type: str,
    *,
    platform_user_id: str | None = None,
    clerk_user_id: str | None = None,
    email: str | None = None,
    name: str | None = None,
    reason: str | None = None,
) -> PlatformUserAuthorizeResponse:
    """Activate / approve portal access. Does not grant super_admin to staff."""
    require_platform_user_type(user_type)
    if user_type == "customer":
        raise ValueError("customer_self_signup_only")
    if not platform_user_id and not clerk_user_id and not email:
        raise ValueError("platform_user_id_clerk_user_id_or_email_required")

    resolved_clerk_id = clerk_user_id
    resolved_platform_id = platform_user_id
    if resolved_platform_id and resolved_platform_id.startswith("clerk:"):
        resolved_clerk_id = resolved_clerk_id or resolved_platform_id.removeprefix("clerk:")
        resolved_platform_id = None

    actions: list[str] = []

    if user_type == "staff":
        return _authorize_staff(
            db,
            ctx,
            platform_user_id=resolved_platform_id,
            clerk_user_id=resolved_clerk_id,
            email=email,
            name=name,
            reason=reason,
            actions=actions,
        )
    if user_type == "driver":
        return _authorize_driver(
            db,
            ctx,
            settings,
            platform_user_id=resolved_platform_id,
            clerk_user_id=resolved_clerk_id,
            email=email,
            name=name,
            reason=reason,
            actions=actions,
        )
    return _authorize_merchant(
        db,
        ctx,
        platform_user_id=resolved_platform_id,
        clerk_user_id=resolved_clerk_id,
        email=email,
        name=name,
        reason=reason,
        actions=actions,
    )


def _admin_modules_for_role(role: AdminRole) -> list[str]:
    return sorted(m for m, allowed in MODULE_PERMISSIONS.items() if role in allowed)


def _merchant_modules_for_role(role: MerchantRole) -> list[str]:
    return sorted(m for m, allowed in MERCHANT_MODULE_PERMISSIONS.items() if role in allowed)


def _sync_authz_for_clerk(db: Session, clerk_user_id: str | None) -> None:
    """Activate registry user + push SpiceDB tuples after authorize mutations."""
    from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

    sync_authz_after_persona_mutation(db, clerk_user_id)


def _authorize_staff(
    db: Session,
    ctx: AdminContext,
    *,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
    name: str | None,
    reason: str | None,
    actions: list[str],
) -> PlatformUserAuthorizeResponse:
    """Activate an enrolled AdminUser. Never creates staff; never forces super_admin.

    Staff IdP owns identity — Clerk ``user_…`` link/promote paths are retired.
    """
    _ = name  # display-only; role comes from enroll / role PATCH
    user = _find_staff(db, platform_user_id, clerk_user_id, email)
    if not user:
        raise LookupError("staff_not_found_invite_first")
    if clerk_user_id and clerk_user_id.startswith("user_"):
        raise ValueError("staff_clerk_retired_use_staff_idp")
    if not user.is_active:
        user.is_active = True
        actions.append("activated")
    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

    ensure_staff_identity(db, user)
    if not actions:
        actions.append("already_authorized")
    log_admin_audit(
        db,
        ctx,
        action="settings.user.authorize",
        resource_type="admin_user",
        resource_id=user.id,
        payload={"user_type": "staff", "role": user.role, "actions": actions, "reason": reason},
    )
    db.commit()
    db.refresh(user)
    _sync_authz_for_clerk(db, user.clerk_user_id)
    role = parse_admin_role(user.role)
    return PlatformUserAuthorizeResponse(
        platform_user_id=user.id,
        user_type="staff",
        email=user.email,
        role=user.role,
        access_status="authorized" if user.is_active else "inactive",
        modules=_admin_modules_for_role(role),
        actions_taken=actions,
    )


def _authorize_driver(
    db: Session,
    ctx: AdminContext,
    settings: Settings,
    *,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
    name: str | None,
    reason: str | None,
    actions: list[str],
) -> PlatformUserAuthorizeResponse:
    driver = _find_driver(db, platform_user_id, clerk_user_id, email)
    if not driver:
        if not email:
            raise LookupError("driver_not_found")
        driver = Driver(
            id=str(uuid.uuid4()),
            full_name=name or email.split("@")[0],
            email=email.lower().strip(),
            clerk_user_id=clerk_user_id,
            status=DriverStatus.PENDING.value,
        )
        db.add(driver)
        db.flush()
        actions.append("created_driver_row")
    elif clerk_user_id and driver.clerk_user_id != clerk_user_id:
        driver.clerk_user_id = clerk_user_id
        actions.append("linked_clerk_id")

    if driver.status != DriverStatus.APPROVED.value:
        AdminDriverService().approve_driver(db, ctx, driver.id, settings)
        actions.append("approved_driver")
        db.refresh(driver)
    elif not actions:
        actions.append("already_authorized")

    log_admin_audit(
        db,
        ctx,
        action="settings.user.authorize",
        resource_type="driver",
        resource_id=driver.id,
        payload={"user_type": "driver", "actions": actions, "reason": reason},
    )
    db.commit()
    db.refresh(driver)
    _sync_authz_for_clerk(db, driver.clerk_user_id)
    return PlatformUserAuthorizeResponse(
        platform_user_id=driver.id,
        user_type="driver",
        email=driver.email,
        role="driver",
        access_status="authorized",
        modules=["driver_portal", "mobile", "dispatch", "earnings", "documents"],
        actions_taken=actions,
    )


def _authorize_merchant(
    db: Session,
    ctx: AdminContext,
    *,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
    name: str | None,
    reason: str | None,
    actions: list[str],
) -> PlatformUserAuthorizeResponse:
    merchant_user = _find_merchant_user(db, platform_user_id, clerk_user_id, email)
    if not merchant_user:
        if not email:
            raise LookupError("merchant_user_not_found")
        normalized = email.lower().strip()
        merchant = get_merchant_by_email(db, normalized)
        if not merchant:
            merchant = create_onboarding_merchant(
                db,
                company_name=name or normalized.split("@")[0].title(),
                email=normalized,
                status=MerchantStatus.ACTIVE.value,
                activated_at=datetime.now(UTC),
                profile={"source": "admin_authorize"},
            )
            actions.append("created_merchant_org")
        merchant_user = ensure_merchant_seat(
            db,
            merchant_id=merchant.id,
            email=normalized,
            role=MerchantRole.OWNER.value,
            actor_user_id=ctx.user.id,
            audit_action="merchant.authorize_owner_seat",
            commit=False,
        )
        bind_seat_clerk(
            db,
            merchant_user.id,
            clerk_user_id or f"pending:{normalized}",
            activate=True,
        )
        actions.append("created_merchant_user")
    else:
        if clerk_user_id and merchant_user.clerk_user_id != clerk_user_id:
            bind_seat_clerk(db, merchant_user.id, clerk_user_id)
            actions.append("linked_clerk_id")

    merchant = get_merchant(db, merchant_user.merchant_id)
    if not merchant:
        raise LookupError("merchant_not_found")

    if merchant_user.role != MerchantRole.OWNER.value:
        actions.append(f"role:{merchant_user.role}->merchant_owner")
        merchant_user.role = MerchantRole.OWNER.value
    if not merchant_user.is_active:
        merchant_user.is_active = True
        actions.append("activated_merchant_user")

    if merchant.status != MerchantStatus.ACTIVE.value:
        AdminMerchantService().approve_merchant(db, ctx, merchant.id)
        actions.append("approved_merchant_org")
        db.refresh(merchant)
    elif not actions:
        actions.append("already_authorized")

    log_admin_audit(
        db,
        ctx,
        action="settings.user.authorize",
        resource_type="merchant_user",
        resource_id=merchant_user.id,
        payload={
            "user_type": "merchant",
            "merchant_id": merchant.id,
            "role": merchant_user.role,
            "actions": actions,
            "reason": reason,
        },
    )
    db.commit()
    db.refresh(merchant_user)
    _sync_authz_for_clerk(db, merchant_user.clerk_user_id)
    role = (
        MerchantRole(merchant_user.role)
        if merchant_user.role in {r.value for r in MerchantRole}
        else MerchantRole.OWNER
    )
    return PlatformUserAuthorizeResponse(
        platform_user_id=merchant_user.id,
        user_type="merchant",
        email=merchant_user.email,
        role=merchant_user.role,
        access_status="authorized",
        modules=_merchant_modules_for_role(role),
        actions_taken=actions,
    )


def _find_staff(
    db: Session,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
) -> AdminUser | None:
    if platform_user_id:
        row = db.query(AdminUser).filter(AdminUser.id == platform_user_id).first()
        if row:
            return row
    if clerk_user_id:
        row = db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first()
        if row:
            return row
    if email:
        return db.query(AdminUser).filter(AdminUser.email == email.lower().strip()).first()
    return None


def _find_driver(
    db: Session,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
) -> Driver | None:
    if platform_user_id:
        row = db.query(Driver).filter(Driver.id == platform_user_id).first()
        if row:
            return row
    if clerk_user_id:
        row = db.query(Driver).filter(Driver.clerk_user_id == clerk_user_id).first()
        if row:
            return row
    if email:
        return db.query(Driver).filter(Driver.email == email.lower().strip()).first()
    return None


def _find_merchant_user(
    db: Session,
    platform_user_id: str | None,
    clerk_user_id: str | None,
    email: str | None,
) -> Any | None:
    if platform_user_id:
        row = get_merchant_user(db, platform_user_id)
        if row:
            return row
    if clerk_user_id:
        seats = seats_for_clerk(db, clerk_user_id)
        if seats:
            return seats[0]
    if email:
        return get_merchant_user_by_email(db, email.lower().strip())
    return None

