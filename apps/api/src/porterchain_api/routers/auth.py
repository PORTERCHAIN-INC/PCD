"""Authentication and SSO — Clerk is the sole identity provider."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.admin import get_admin_context
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.fleetbase_roles import can_access_fleetbase_console
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.auth.enterprise_rbac import (
    enterprise_role_for_merchant,
    principal_enterprise_payload,
    rbac_matrix,
)
from porterchain_api.auth.customer import CustomerContext, get_customer_context, resolve_customer_contact
from porterchain_api.auth.customer_onboarding import evaluate_customer_onboarding
from porterchain_api.auth.merchant_onboarding import evaluate_merchant_onboarding, save_merchant_vertical
from porterchain_api.auth.merchant import get_merchant_context
from porterchain_api.merchant_engine.rbac import MerchantContext, parse_merchant_role
from porterchain_api.schemas_auth import (
    AdminAccessResponse,
    AuthMeResponse,
    CustomerAccessResponse,
    FleetbaseSsoResponse,
    MerchantAccessResponse,
    MerchantVerticalRequest,
    PortalOnboardingResponse,
    RbacMatrixResponse,
)
from porterchain_shared.types.user_types import UserType

router = APIRouter(prefix="/v1/auth", tags=["auth"])
_sso = SsoService()


@router.get("/me", response_model=AuthMeResponse)
def auth_me(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AuthMeResponse:
    """Current user principal — roles and permissions from Porterchain RBAC."""
    principal = _sso.resolve_principal(db, claims, settings)
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")

    fleetbase_eligible = False
    if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
        admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
        if admin:
            fleetbase_eligible = can_access_fleetbase_console(parse_admin_role(admin.role))

    payload = _sso.session_payload(principal)
    payload.update(principal_enterprise_payload(db, principal))
    payload["fleetbase_console_eligible"] = fleetbase_eligible

    pc_user = UserSyncService().get_by_clerk_id(db, claims.clerk_user_id)
    if pc_user:
        payload["clerk_user_id"] = pc_user.clerk_user_id
        payload["phone"] = pc_user.phone
        payload["role"] = pc_user.role
        payload["status"] = pc_user.status
        payload["profile"] = pc_user.profile

    return AuthMeResponse(**payload)


@router.get("/rbac", response_model=RbacMatrixResponse)
def auth_rbac(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> RbacMatrixResponse:
    """Enterprise RBAC matrix and current user's effective access."""
    principal = _sso.resolve_principal(db, claims, settings)
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")
    ent = principal_enterprise_payload(db, principal)
    return RbacMatrixResponse(
        matrix=rbac_matrix(),
        enterprise_role=ent["enterprise_role"],
        enterprise_permissions=ent["enterprise_permissions"],
        admin_modules=ent["admin_modules"],
        merchant_modules=ent["merchant_modules"],
    )


@router.get("/merchant/access", response_model=MerchantAccessResponse)
def merchant_access(
    ctx: Annotated[MerchantContext, Depends(get_merchant_context)],
) -> MerchantAccessResponse:
    """Verify merchant portal access from Porterchain merchant_users (not Clerk orgs)."""
    m_role = parse_merchant_role(ctx.user.role)
    return MerchantAccessResponse(
        user_id=ctx.user.id,
        merchant_id=ctx.merchant.id,
        email=ctx.user.email,
        merchant_role=ctx.user.role,
        enterprise_role=enterprise_role_for_merchant(m_role).value,
        company_name=ctx.merchant.company_name or "",
        is_active=ctx.user.is_active,
    )


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


@router.get("/customer/access", response_model=CustomerAccessResponse)
def customer_access(
    ctx: Annotated[CustomerContext, Depends(get_customer_context)],
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
) -> CustomerAccessResponse:
    """Verify customer portal access — provisions customers row on first sign-in."""
    return CustomerAccessResponse(
        customer_id=ctx.customer.id,
        email=ctx.email,
        clerk_user_id=claims.clerk_user_id,
        is_active=True,
    )


@router.get("/customer/onboarding", response_model=PortalOnboardingResponse)
def customer_onboarding(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """Customer activation checklist."""
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


@router.get("/admin/access", response_model=AdminAccessResponse)
def admin_access(
    ctx: Annotated[AdminContext, Depends(get_admin_context)],
) -> AdminAccessResponse:
    """Verify the signed-in Clerk user is provisioned staff (admin_users table)."""
    user = ctx.user
    return AdminAccessResponse(
        user_id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        is_active=user.is_active,
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
