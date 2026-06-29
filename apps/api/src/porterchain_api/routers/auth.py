"""Authentication and SSO — Clerk is the sole identity provider."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.fleetbase_roles import can_access_fleetbase_console
from porterchain_api.auth.sso_service import SsoService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.schemas_auth import AuthMeResponse, FleetbaseSsoResponse
from porterchain_shared.types.user_types import UserType

router = APIRouter(prefix="/v1/auth", tags=["auth"])
_sso = SsoService()


@router.get("/me", response_model=AuthMeResponse)
def auth_me(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
) -> AuthMeResponse:
    """Current user principal — roles and permissions from Porterchain RBAC."""
    principal = _sso.resolve_principal(db, claims)
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")

    fleetbase_eligible = False
    if principal.user_type in (UserType.ADMIN, UserType.DISPATCHER, UserType.SUPPORT):
        admin = db.query(AdminUser).filter(AdminUser.id == principal.user_id).first()
        if admin:
            fleetbase_eligible = can_access_fleetbase_console(parse_admin_role(admin.role))

    payload = _sso.session_payload(principal)
    payload["fleetbase_console_eligible"] = fleetbase_eligible
    return AuthMeResponse(**payload)


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

    principal = _sso.resolve_principal(db, claims)
    if not principal:
        raise HTTPException(status_code=403, detail="user_not_provisioned")

    try:
        result = _sso.exchange_fleetbase_session(db, settings, claims, principal)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return FleetbaseSsoResponse(**result)
