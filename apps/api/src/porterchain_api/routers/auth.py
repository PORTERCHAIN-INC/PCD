"""Authentication and SSO — Clerk for business portals; staff IdP for admin."""

from collections.abc import Callable
from typing import Annotated, TypeVar

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.staff_idp_service import StaffIdpService
from porterchain_api.auth import staff_webauthn
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.customer_onboarding import customer_onboarding_payload
from porterchain_api.auth.dependencies import require_authenticated
from porterchain_api.auth.merchant_onboarding import (
    evaluate_merchant_onboarding,
    save_merchant_company_file,
    save_merchant_vertical,
)
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.auth.staff_rate_limit import enforce_staff_auth_rate
from porterchain_api.auth.sli_metrics import note_auth_event
from porterchain_api.auth.staff_session import (
    STAFF_COOKIE_NAME,
    assert_recent_step_up,
    attach_session_cookie,
    authentication_options_for_email,
    clear_session_cookie,
    client_meta_from_request,
    delete_passkey,
    get_session,
    list_passkeys,
    list_sessions_for_user,
    login_from_body,
    mark_step_up,
    passkey_credential_payload,
    peek_enrollment,
    revoke_all_for_user,
    revoke_session,
    session_id_from_authorization,
    staff_cookie_params,
    verify_registration_from_body,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_auth import (
    AuthMeResponse,
    MerchantVerticalRequest,
    PortalOnboardingResponse,
    SessionContextResponse,
)
from porterchain_api.schemas_merchant import MerchantProfileUpdateRequest

router = APIRouter(prefix="/v1/auth", tags=["auth"])
_sso = SsoService()
T = TypeVar("T")
_AUTH_UNAVAILABLE = ("redis", "unavailable")


def _invoke(fn: Callable[..., T], *args: object, **kwargs: object) -> T:
    try:
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        detail = str(exc)
        status = 503 if any(token in detail for token in _AUTH_UNAVAILABLE) else 400
        raise HTTPException(status_code=status, detail=detail) from exc


def _staff_session_response(payload: dict, settings: Settings):
    return attach_session_cookie(JSONResponse(payload), payload, settings)


def _current_staff_sid(request: Request, authorization: str | None) -> str | None:
    return session_id_from_authorization(authorization) or request.cookies.get(STAFF_COOKIE_NAME)


@router.get("/me", response_model=AuthMeResponse)
def auth_me(
    principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
    db: Session = Depends(get_db),
) -> AuthMeResponse:
    """Current user principal — roles/permissions from SpiceDB-backed CurrentPrincipal."""
    return AuthMeResponse(**principal.me_payload(db))


@router.get("/session-context", response_model=SessionContextResponse)
def auth_session_context(
    principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
) -> SessionContextResponse:
    """Unified session context — permissions/workspaces from SpiceDB."""
    return SessionContextResponse(**principal.session_context_cached())


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
    return PortalOnboardingResponse(
        **save_merchant_vertical(
            db, claims, body.vertical, settings=settings, attribution=body.attribution
        )
    )


@router.patch("/merchant/onboarding/profile", response_model=PortalOnboardingResponse)
def merchant_onboarding_profile(
    body: MerchantProfileUpdateRequest,
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """ONBOARDING owners finish the company file before ops activates the account."""
    return PortalOnboardingResponse(**save_merchant_company_file(db, claims, body, settings=settings))


@router.get("/customer/onboarding", response_model=PortalOnboardingResponse)
def customer_onboarding(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> PortalOnboardingResponse:
    """Customer activation checklist — provisions customers row when allowed."""
    return PortalOnboardingResponse(**customer_onboarding_payload(db, claims, settings))


from porterchain_api.routers import auth_staff as _auth_staff  # noqa: F401
from porterchain_api.routers import auth_staff_sessions as _auth_staff_sessions  # noqa: F401

# Re-exports kept for existing importers (integration).
from porterchain_api.auth import staff_webauthn  # noqa: E402, F401
from porterchain_api.auth.staff_session import get_session  # noqa: E402, F401
from porterchain_api.auth.staff_session import list_sessions_for_user  # noqa: E402, F401
from porterchain_api.admin_engine.staff_idp_service import StaffIdpService  # noqa: E402, F401
from porterchain_api.auth.staff_rate_limit import enforce_staff_auth_rate  # noqa: E402, F401
from porterchain_api.auth.sli_metrics import note_auth_event  # noqa: E402, F401
from porterchain_api.auth.staff_session import assert_recent_step_up  # noqa: E402, F401
from porterchain_api.auth.staff_session import authentication_options_for_email  # noqa: E402, F401
from porterchain_api.auth.staff_session import clear_session_cookie  # noqa: E402, F401
from porterchain_api.auth.staff_session import client_meta_from_request  # noqa: E402, F401
from porterchain_api.auth.staff_session import delete_passkey  # noqa: E402, F401
from porterchain_api.auth.staff_session import list_passkeys  # noqa: E402, F401
from porterchain_api.auth.staff_session import login_from_body  # noqa: E402, F401
from porterchain_api.auth.staff_session import mark_step_up  # noqa: E402, F401
from porterchain_api.auth.staff_session import passkey_credential_payload  # noqa: E402, F401
from porterchain_api.auth.staff_session import peek_enrollment  # noqa: E402, F401
from porterchain_api.auth.staff_session import revoke_all_for_user  # noqa: E402, F401
from porterchain_api.auth.staff_session import revoke_session  # noqa: E402, F401
from porterchain_api.auth.staff_session import staff_cookie_params  # noqa: E402, F401
from porterchain_api.auth.staff_session import verify_registration_from_body  # noqa: E402, F401
