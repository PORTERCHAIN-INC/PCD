"""Authentication and SSO — Clerk for business portals; staff IdP for admin."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
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
    from porterchain_api.auth.customer import require_customer
    from porterchain_api.auth.portal_guard import clerk_id_staff_portal

    email, _phone = resolve_customer_contact(db, claims, settings)
    customer = None
    if claims.clerk_user_id and not clerk_id_staff_portal(db, claims.clerk_user_id):
        try:
            customer = require_customer(db, claims, settings)
            db.commit()
        except HTTPException:
            customer = None
    return PortalOnboardingResponse(
        **evaluate_customer_onboarding(
            db, claims, settings=settings, customer=customer, email=email
        )
    )


@router.post("/sso/fleetbase", response_model=FleetbaseSsoResponse)
def sso_fleetbase(
    principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> FleetbaseSsoResponse:
    """
    Exchange staff IdP (or legacy Clerk) session for Fleetbase console SSO.
    Fleetbase trusts Porterchain JWT — no Fleetbase login screen for Porterchain users.
    """
    if not settings.fleetbase_sso_enabled:
        raise HTTPException(status_code=503, detail="fleetbase_sso_disabled")

    try:
        result = _sso.exchange_fleetbase_session_for_principal(db, settings, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FleetbaseSsoResponse(**result)


@router.get("/staff/enrollment/{token}")
def peek_staff_enrollment(token: str) -> dict:
    """Public peek for staff IdP activation UI (no Clerk)."""
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService

    enrollment = StaffIdpService().peek(token)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="enrollment_invalid_or_expired")
    return {
        "email": enrollment.email,
        "role": enrollment.role,
        "expires_at": enrollment.expires_at,
    }


@router.post("/staff/enrollment/{token}/activate")
def activate_staff_enrollment(
    token: str,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Consume enrollment token, mint Redis session, set ``pc_staff_sid`` cookie."""
    from fastapi.responses import JSONResponse

    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
    from porterchain_api.auth.staff_session import staff_cookie_params

    try:
        payload = StaffIdpService().activate(db, token)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    response = JSONResponse(payload)
    cookie = staff_cookie_params(settings)
    response.set_cookie(
        cookie["key"],
        payload["session_id"],
        max_age=cookie["max_age"],
        httponly=cookie["httponly"],
        secure=cookie["secure"],
        samesite=cookie["samesite"],
        path=cookie["path"],
        domain=cookie["domain"],
    )
    return response


@router.post("/staff/login-request")
def staff_login_request(
    body: dict,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Email a one-time staff login link (token included only in local env)."""
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService

    email = (body.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="email_required")
    try:
        return StaffIdpService().request_login(db, settings, email=email)
    except ValueError as exc:
        detail = str(exc)
        if detail == "staff_enrollment_redis_unavailable":
            raise HTTPException(status_code=503, detail=detail) from exc
        raise HTTPException(status_code=400, detail=detail) from exc


def _staff_session_response(payload: dict, settings: Settings):
    from fastapi.responses import JSONResponse

    from porterchain_api.auth.staff_session import staff_cookie_params

    response = JSONResponse(payload)
    cookie = staff_cookie_params(settings)
    response.set_cookie(
        cookie["key"],
        payload["session_id"],
        max_age=cookie["max_age"],
        httponly=cookie["httponly"],
        secure=cookie["secure"],
        samesite=cookie["samesite"],
        path=cookie["path"],
        domain=cookie["domain"],
    )
    return response


@router.post("/staff/passkey/register/options")
async def staff_passkey_register_options(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WebAuthn registration options for an authenticated staff session."""
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.auth import staff_webauthn

    ctx = await get_admin_context(request, authorization, db, settings, None)
    try:
        return staff_webauthn.registration_options(db, settings, ctx.user)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/staff/passkey/register/verify")
async def staff_passkey_register_verify(
    body: dict,
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Verify WebAuthn registration and persist credential."""
    from porterchain_api.auth.admin import get_admin_context
    from porterchain_api.auth import staff_webauthn

    ctx = await get_admin_context(request, authorization, db, settings, None)
    challenge_id = (body.get("challenge_id") or "").strip()
    credential = body.get("credential")
    if not challenge_id or not isinstance(credential, dict):
        raise HTTPException(status_code=400, detail="passkey_registration_invalid")
    try:
        row = staff_webauthn.verify_registration(
            db,
            settings,
            admin_user=ctx.user,
            challenge_id=challenge_id,
            credential=credential,
            device_label=body.get("device_label"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": row.id,
        "credential_id": row.credential_id,
        "device_label": row.device_label,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


@router.post("/staff/passkey/login/options")
def staff_passkey_login_options(
    body: dict,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """WebAuthn authentication options for staff email (public)."""
    from porterchain_api.auth import staff_webauthn

    email = (body.get("email") or "").strip()
    if not email:
        raise HTTPException(status_code=400, detail="email_required")
    try:
        return staff_webauthn.authentication_options(db, settings, email=email)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/staff/login")
def staff_login(
    body: dict,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    """Activate via enrollment_token or passkey_assertion. Sets staff session cookie."""
    from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
    from porterchain_api.auth import staff_webauthn

    assertion = body.get("passkey_assertion")
    if assertion:
        challenge_id = (body.get("challenge_id") or assertion.get("challenge_id") or "").strip()
        credential = assertion.get("credential") if isinstance(assertion, dict) else None
        if credential is None and isinstance(assertion, dict) and assertion.get("id"):
            credential = assertion
        if not challenge_id or not isinstance(credential, dict):
            raise HTTPException(status_code=400, detail="passkey_assertion_invalid")
        try:
            payload = staff_webauthn.verify_authentication(
                db, settings, challenge_id=challenge_id, credential=credential
            )
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            detail = str(exc)
            status = 503 if "redis" in detail else 400
            raise HTTPException(status_code=status, detail=detail) from exc
        return _staff_session_response(payload, settings)

    enrollment_token = (body.get("enrollment_token") or "").strip()
    if not enrollment_token:
        raise HTTPException(status_code=400, detail="enrollment_token_required")
    try:
        payload = StaffIdpService().activate(db, enrollment_token)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _staff_session_response(payload, settings)


@router.post("/staff/logout")
def staff_logout(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
):
    """Revoke staff session + clear cookie."""
    from fastapi.responses import JSONResponse

    from porterchain_api.auth.staff_session import (
        STAFF_COOKIE_NAME,
        revoke_session,
        session_id_from_authorization,
        staff_cookie_params,
    )

    sid = session_id_from_authorization(authorization) or request.cookies.get(STAFF_COOKIE_NAME)
    if sid:
        revoke_session(sid)
    response = JSONResponse({"ok": True})
    cookie = staff_cookie_params(settings, max_age=0)
    response.delete_cookie(
        cookie["key"],
        path=cookie["path"],
        domain=cookie["domain"],
        secure=cookie["secure"],
        httponly=cookie["httponly"],
        samesite=cookie["samesite"],
    )
    return response
