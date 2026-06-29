from typing import Annotated

from fastapi import Depends, Header, HTTPException
from jose import JWTError, jwk, jwt
import httpx

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.config import Settings, get_settings

_jwks_cache: dict | None = None


async def _get_jwks(settings: Settings) -> dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    if not settings.clerk_jwks_url:
        return {}
    async with httpx.AsyncClient() as client:
        response = await client.get(settings.clerk_jwks_url, timeout=10.0)
        response.raise_for_status()
        _jwks_cache = response.json()
        return _jwks_cache


def _rsa_key_for_token(jwks: dict, token: str):
    header = jwt.get_unverified_header(token)
    kid = header.get("kid")
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data)
    return None


def _dev_claims() -> ClerkClaims:
    return ClerkClaims(
        clerk_user_id="dev_clerk_user",
        email="admin@porterchain.com",
        org_id=None,
        org_role="dispatcher",
        public_metadata={"role": "dispatcher"},
        session_id="dev_session",
    )


async def verify_clerk_token(token: str, settings: Settings) -> ClerkClaims:
    if token == "dev" and settings.app_env == "local":
        return _dev_claims()

    jwks = await _get_jwks(settings)
    if not jwks.get("keys"):
        raise HTTPException(status_code=503, detail="clerk_not_configured")
    rsa_key = _rsa_key_for_token(jwks, token)
    if not rsa_key:
        raise HTTPException(status_code=401, detail="invalid_token")
    try:
        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_token")

    return ClerkClaims(
        clerk_user_id=user_id,
        email=payload.get("email"),
        org_id=payload.get("org_id"),
        org_role=payload.get("org_role"),
        public_metadata=payload.get("public_metadata") if isinstance(payload.get("public_metadata"), dict) else None,
        session_id=payload.get("sid"),
    )


async def get_clerk_claims(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> ClerkClaims:
    if settings.clerk_dev_bypass and not authorization:
        return _dev_claims()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    token = authorization.removeprefix("Bearer ").strip()
    return await verify_clerk_token(token, settings)


async def get_clerk_user_id(claims: ClerkClaims = Depends(get_clerk_claims)) -> str:
    return claims.clerk_user_id
