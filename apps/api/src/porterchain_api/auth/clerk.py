from typing import Annotated

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwk, jwt
import httpx
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_registry import clerk_jwks_urls
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.user_sync_service import UserSyncService
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db

_jwks_cache: dict[str, dict] = {}


async def _get_jwks(url: str) -> dict:
    if url in _jwks_cache:
        return _jwks_cache[url]
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache[url] = response.json()
        return _jwks_cache[url]


def _rsa_key_for_token(jwks: dict, token: str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)
    return None


def _claims_from_payload(payload: dict, *, clerk_app: str | None = None) -> ClerkClaims:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_token")
    return ClerkClaims(
        clerk_user_id=user_id,
        email=payload.get("email"),
        phone=payload.get("phone_number") or payload.get("primary_phone_number"),
        org_id=payload.get("org_id"),
        org_role=payload.get("org_role"),
        public_metadata=payload.get("public_metadata") if isinstance(payload.get("public_metadata"), dict) else None,
        session_id=payload.get("sid"),
        clerk_app=clerk_app,
    )


def _dev_claims() -> ClerkClaims:
    return ClerkClaims(
        clerk_user_id="dev_clerk_user",
        email="admin@porterchain.com",
        org_id=None,
        org_role="dispatcher",
        public_metadata={"role": "dispatcher"},
        session_id="dev_session",
        clerk_app="admin",
    )


async def verify_clerk_token(token: str, settings: Settings) -> ClerkClaims:
    if token == "dev" and allow_auth_dev_bypass(settings):
        return _dev_claims()

    jwks_entries = clerk_jwks_urls(settings)
    if not jwks_entries:
        raise HTTPException(status_code=503, detail="clerk_not_configured")

    last_error: JWTError | None = None
    for clerk_app, jwks_url in jwks_entries:
        jwks = await _get_jwks(jwks_url)
        if not jwks.get("keys"):
            continue
        rsa_key = _rsa_key_for_token(jwks, token)
        if not rsa_key:
            continue
        try:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options={"verify_aud": False},
            )
            return _claims_from_payload(payload, clerk_app=clerk_app)
        except JWTError as exc:
            last_error = exc
            continue

    if last_error:
        raise HTTPException(status_code=401, detail="invalid_token") from last_error
    raise HTTPException(status_code=401, detail="invalid_token")


async def get_clerk_claims(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> ClerkClaims:
    if allow_auth_dev_bypass(settings) and not authorization:
        claims = _dev_claims()
    elif not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    else:
        token = authorization.removeprefix("Bearer ").strip()
        claims = await verify_clerk_token(token, settings)

    UserSyncService().sync(db, claims)
    return claims


async def get_clerk_user_id(claims: ClerkClaims = Depends(get_clerk_claims)) -> str:
    return claims.clerk_user_id


async def get_optional_clerk_user_id(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> str | None:
    """Return Clerk user id when a valid bearer token is present; otherwise None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if token == "dev" and allow_auth_dev_bypass(settings):
        claims = _dev_claims()
    else:
        try:
            claims = await verify_clerk_token(token, settings)
        except HTTPException:
            return None
    UserSyncService().sync(db, claims)
    return claims.clerk_user_id
