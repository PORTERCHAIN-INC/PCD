"""FastAPI Clerk claim dependencies — thin wrapper over KeycloakIdentityProvider."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.identity_provider import (
    _dev_claims,
    verify_access_token,
)
from porterchain_api.auth.dev import DEV_PORTAL_HEADER, allow_auth_dev_bypass
from porterchain_api.auth.prepare import prepare_user_from_claims
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from starlette.concurrency import run_in_threadpool

# Re-export for existing imports
__all__ = [
    "IdentityClaims",
    "verify_access_token",
    "get_identity_claims",
    "get_auth_subject",
    "get_optional_auth_subject",
    "_sync_and_ensure",
]


def _sync_and_ensure(db: Session, claims: IdentityClaims) -> IdentityClaims:
    """Single auth prepare path (request-cached via prepare_user_from_claims)."""
    prepare_user_from_claims(db, claims)
    return claims


def _portal_header(request: Request | None, explicit: str | None) -> str | None:
    if explicit and explicit.strip():
        return explicit
    if request is None:
        return None
    return request.headers.get(DEV_PORTAL_HEADER)


def _request_path(request: Request | None) -> str:
    if request is None:
        return ""
    return request.url.path


async def get_identity_claims(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    x_porterchain_portal: Annotated[str | None, Header()] = None,
) -> IdentityClaims:
    portal_header = _portal_header(request, x_porterchain_portal)
    path = _request_path(request)
    if allow_auth_dev_bypass(settings) and (not authorization or authorization == "Bearer dev"):
        return (await run_in_threadpool(lambda: _sync_and_ensure(db, _dev_claims(path=path, header=portal_header))))

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")

    token = authorization.removeprefix("Bearer ").strip()
    if token == "dev":
        if not allow_auth_dev_bypass(settings):
            raise HTTPException(status_code=401, detail="dev_bypass_disabled")
        return (await run_in_threadpool(lambda: _sync_and_ensure(db, _dev_claims(path=path, header=portal_header))))

    from porterchain_api.auth.impersonation_session import (
        IMP_BEARER_PREFIX,
        resolve_from_bearer,
    )

    if token.startswith(IMP_BEARER_PREFIX):
        session = resolve_from_bearer(token)
        if not session:
            raise HTTPException(status_code=401, detail="impersonation_expired")
        portal = (portal_header or "").strip().lower()
        if portal in ("driver", "merchant", "customer") and portal != session.target_type:
            raise HTTPException(status_code=403, detail="impersonation_portal_mismatch")
        request.state.impersonation = session
        # Synthetic claims — never a forged Clerk JWT. Persona resolvers key off metadata.
        return IdentityClaims(
            clerk_user_id=session.target_clerk_user_id
            or f"impersonation:{session.target_id}",
            email=session.target_email,
            public_metadata={
                "impersonation": True,
                "user_type": session.target_type,
                "target_id": session.target_id,
                "actor_admin_id": session.actor_admin_id,
                "session_id": session.session_id,
            },
        )

    claims = await verify_access_token(token, settings, path=path, header=portal_header)
    return (await run_in_threadpool(lambda: _sync_and_ensure(db, claims)))


async def get_auth_subject(claims: IdentityClaims = Depends(get_identity_claims)) -> str:
    return claims.clerk_user_id


async def get_optional_auth_subject(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    x_porterchain_portal: Annotated[str | None, Header()] = None,
) -> str | None:
    """Return Clerk user id when a valid bearer token is present; otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    portal_header = _portal_header(request, x_porterchain_portal)
    path = _request_path(request)
    if token == "dev":
        if not allow_auth_dev_bypass(settings):
            return None
        claims = _dev_claims(path=path, header=portal_header)
    else:
        try:
            claims = await verify_access_token(token, settings, path=path, header=portal_header)
        except HTTPException:
            return None
    (await run_in_threadpool(lambda: _sync_and_ensure(db, claims)))
    return claims.clerk_user_id
