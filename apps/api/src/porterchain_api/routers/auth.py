"""Authentication and SSO — Clerk is the sole identity provider."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.customer_onboarding import evaluate_customer_onboarding
from porterchain_api.auth.customer import resolve_customer_contact
from porterchain_api.auth.dependencies import require_authenticated
from porterchain_api.auth.fleetbase_roles import can_access_fleetbase_console
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding, save_merchant_vertical
from porterchain_api.auth.modules_catalog import modules_for_permissions
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.auth.unified_catalog import UnifiedPermission
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_auth import (
    AuthMeResponse,
    FleetbaseSsoResponse,
    MerchantVerticalRequest,
    PortalOnboardingResponse,
    SessionContextResponse,
)
from porterchain_shared.types.user_types import UserType

router = APIRouter(prefix="/v1/auth", tags=["auth"])
_sso = SsoService()


def _deprecated_user_type_hint(principal: CurrentPrincipal) -> str:
    """Legacy exclusive user_type for older clients — not an authz signal.

    Never default to customer: that routed unprovisioned / SpiceDB-miss users into
    the retail portal. Prefer permission Checks, then Postgres-backed roles.
    """
    from porterchain_api.auth.unified_catalog import AssignableRole

    if principal.has_any_permission(
        UnifiedPermission.PLATFORM_ADMIN_ACCESS,
        UnifiedPermission.SYSTEM_ALL,
    ):
        return UserType.ADMIN.value
    if principal.has_permission(UnifiedPermission.MERCHANT_PORTAL_ACCESS):
        return UserType.MERCHANT.value
    if principal.has_permission(UnifiedPermission.DRIVER_PORTAL_ACCESS):
        return UserType.DRIVER.value
    if principal.has_permission(UnifiedPermission.CUSTOMER_PORTAL_ACCESS):
        return UserType.CUSTOMER.value

    staff = {
        AssignableRole.SUPER_ADMIN,
        AssignableRole.ADMIN,
        AssignableRole.DISPATCHER,
        AssignableRole.SUPPORT,
        AssignableRole.SUPPORT_LEAD,
        AssignableRole.SALES,
        AssignableRole.SALES_MANAGER,
        AssignableRole.FINANCE,
        AssignableRole.COMPLIANCE,
        AssignableRole.DEVELOPER,
        AssignableRole.MARKETING,
        AssignableRole.READ_ONLY,
        AssignableRole.FLEET_MANAGER,
    }
    if principal.roles & staff:
        return UserType.ADMIN.value
    merchant_roles = {
        AssignableRole.MERCHANT_OWNER,
        AssignableRole.MERCHANT_ADMIN,
        AssignableRole.MERCHANT_OPS,
        AssignableRole.MERCHANT_FINANCE,
        AssignableRole.MERCHANT_READONLY,
    }
    if principal.roles & merchant_roles:
        return UserType.MERCHANT.value
    if AssignableRole.DRIVER in principal.roles:
        return UserType.DRIVER.value
    if AssignableRole.CUSTOMER in principal.roles:
        return UserType.CUSTOMER.value
    return "unprovisioned"


@router.get("/me", response_model=AuthMeResponse)
def auth_me(
    principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
    db: Session = Depends(get_db),
) -> AuthMeResponse:
    """Current user principal — roles/permissions from SpiceDB-backed CurrentPrincipal."""
    sc = principal.session_context()
    user_type = _deprecated_user_type_hint(principal)

    fleetbase_eligible = False
    admin_id = principal.legacy_profile_ids.get("admin_user_id")
    if admin_id and principal.has_any_permission(
        UnifiedPermission.PLATFORM_ADMIN_ACCESS,
        UnifiedPermission.SYSTEM_ALL,
    ):
        admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
        if admin:
            fleetbase_eligible = can_access_fleetbase_console(parse_admin_role(admin.role))

    org_id = next(iter(sorted(principal.organization_ids)), None)
    pc_user = UserSyncService().get_by_clerk_id(db, principal.auth_subject or "")
    primary_role = sc["roles"][0] if sc["roles"] else None
    return AuthMeResponse(
        user_id=principal.user_id,
        clerk_user_id=principal.auth_subject,
        user_type=user_type,
        roles=sc["roles"],
        permissions=sc["permissions"],
        modules=sc.get("modules") or modules_for_permissions(principal.permissions),
        workspaces=sc.get("workspaces") or [],
        organization_ids=sc.get("organization_ids") or [],
        # Deprecated fields — SpiceDB roles/permissions only (not porterchain_users.role hint)
        enterprise_role=primary_role,
        enterprise_permissions=sc["permissions"],
        org_id=org_id,
        email=principal.email,
        phone=pc_user.phone if pc_user else None,
        role=primary_role,
        status=principal.status,
        profile=pc_user.profile if pc_user else None,
        fleetbase_console_eligible=fleetbase_eligible,
    )


@router.get("/session-context", response_model=SessionContextResponse)
def auth_session_context(
    principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
) -> SessionContextResponse:
    """Unified session context — permissions/workspaces from SpiceDB."""
    from porterchain_api.auth.principal_cache import cache_get, cache_set

    cached = cache_get(principal.user_id)
    if cached:
        return SessionContextResponse(**cached)
    payload = principal.session_context()
    cache_set(principal.user_id, payload)
    return SessionContextResponse(**payload)


@router.get("/merchant/onboarding", response_model=PortalOnboardingResponse)
def merchant_onboarding(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """Merchant activation checklist — does not require ACTIVE merchant."""
    return PortalOnboardingResponse(**evaluate_merchant_onboarding(db, claims, settings=settings))


@router.patch("/merchant/onboarding/vertical", response_model=PortalOnboardingResponse)
def merchant_onboarding_vertical(
    body: MerchantVerticalRequest,
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """§8.1.12 — Merchant selects primary business vertical during onboarding."""
    return PortalOnboardingResponse(**save_merchant_vertical(db, claims, body.vertical, settings=settings))


@router.get("/customer/onboarding", response_model=PortalOnboardingResponse)
def customer_onboarding(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """Customer activation checklist — provisions customers row when allowed."""
    from porterchain_api.booking_engine import CustomerService

    email, phone = resolve_customer_contact(db, claims, settings)
    customer = None
    if claims.clerk_user_id:
        from porterchain_api.models import Customer

        customer = db.query(Customer).filter(Customer.clerk_user_id == claims.clerk_user_id).first()
    if not customer and email and claims.clerk_user_id:
        from porterchain_api.auth.portal_guard import clerk_id_staff_portal

        if not clerk_id_staff_portal(db, claims.clerk_user_id):
            try:
                customer = CustomerService().get_or_create_from_clerk(
                    db,
                    clerk_user_id=claims.clerk_user_id,
                    email=email,
                    phone=phone,
                )
                db.commit()
            except ValueError:
                pass
    return PortalOnboardingResponse(
        **evaluate_customer_onboarding(
            db, claims, settings=settings, customer=customer, email=email
        )
    )


@router.post("/sso/fleetbase", response_model=FleetbaseSsoResponse)
def sso_fleetbase(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FleetbaseSsoResponse:
    """
    Exchange Clerk session for Fleetbase console SSO.
    Fleetbase trusts Porterchain JWT — no Fleetbase login screen for Porterchain users.
    """
    if not settings.fleetbase_sso_enabled:
        raise HTTPException(status_code=503, detail="fleetbase_sso_disabled")

    principal = _sso.resolve_principal(db, claims, settings)
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")

    try:
        result = _sso.exchange_fleetbase_session(db, settings, claims, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FleetbaseSsoResponse(**result)
