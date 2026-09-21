"""FastAPI Clerk claim dependencies — thin wrapper over ClerkIdentityProvider."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_identity_provider import (
    _dev_claims,
    verify_clerk_token,
)
from porterchain_api.auth.dev import DEV_PORTAL_HEADER, allow_auth_dev_bypass
from porterchain_api.auth.prepare import prepare_user_from_claims
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db

# Re-export for existing imports
__all__ = [
    "ClerkClaims",
    "verify_clerk_token",
    "get_clerk_claims",
    "get_clerk_user_id",
    "get_optional_clerk_user_id",
    "_sync_and_ensure",
]


def _sync_and_ensure(db: Session, claims: ClerkClaims) -> ClerkClaims:
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


async def get_clerk_claims(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    x_porterchain_portal: Annotated[str | None, Header()] = None,
) -> ClerkClaims:
    portal_header = _portal_header(request, x_porterchain_portal)
    path = _request_path(request)
    if allow_auth_dev_bypass(settings) and (not authorization or authorization == "Bearer dev"):
        return _sync_and_ensure(db, _dev_claims(path=path, header=portal_header))

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")

    token = authorization.removeprefix("Bearer ").strip()
    if token == "dev":
        if not allow_auth_dev_bypass(settings):
            raise HTTPException(status_code=401, detail="dev_bypass_disabled")
        return _sync_and_ensure(db, _dev_claims(path=path, header=portal_header))

    claims = await verify_clerk_token(token, settings, path=path, header=portal_header)
    return _sync_and_ensure(db, claims)


async def get_clerk_user_id(claims: ClerkClaims = Depends(get_clerk_claims)) -> str:
    return claims.clerk_user_id


async def get_optional_clerk_user_id(
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
            claims = await verify_clerk_token(token, settings, path=path, header=portal_header)
        except HTTPException:
            return None
    _sync_and_ensure(db, claims)
    return claims.clerk_user_id
