"""Keycloak OIDC verifier — the only auth provider (AUTH_PROVIDER=keycloak, L36 / doc 74).

Verifies RS256 access tokens from realm ``porterchain`` against its JWKS (cached, refreshed on
unknown ``kid``), enforces ``iss``, ``exp``/``nbf``, audience ``pc-api`` and the ``azp`` client
allowlist, then maps ``sub`` to our identity claims. No network call besides JWKS.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
import jwt
from fastapi import HTTPException
from jwt import PyJWK, PyJWTError

from porterchain_api.auth.claims import IdentityClaims as IdentityClaims
from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

_CLOCK_LEEWAY_S = 10
_JWKS_TTL_S = 600
_jwks_cache: dict[str, tuple[float, dict]] = {}

#: azp (client id) → portal kind, used for portal routing / audit.
CLIENT_PORTAL: dict[str, str] = {
    "pc-website": "customer",
    "pc-customer-portal": "customer",
    "pc-customer-app": "customer",
    "pc-merchant-portal": "merchant",
    "pc-admin": "admin",
    "pc-driver-portal": "driver",
    "pc-driver-app": "driver",
}


def keycloak_issuer(settings: Settings) -> str:
    explicit = (settings.keycloak_issuer or "").strip().rstrip("/")
    if explicit:
        return explicit
    base = (settings.keycloak_url or "").strip().rstrip("/")
    if not base:
        return ""
    return f"{base}/realms/{settings.keycloak_realm}"


def keycloak_jwks_url(settings: Settings) -> str:
    internal = (settings.keycloak_internal_url or "").strip().rstrip("/")
    if internal:
        return f"{internal}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    issuer = keycloak_issuer(settings)
    return f"{issuer}/protocol/openid-connect/certs" if issuer else ""


async def _fetch_jwks(url: str, *, force: bool = False) -> dict:
    now = time.monotonic()
    cached = _jwks_cache.get(url)
    if cached and not force and now - cached[0] < _JWKS_TTL_S:
        return cached[1]
    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    _jwks_cache[url] = (now, data)
    return data


def _key_for(jwks: dict, kid: str | None):
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid and key_data.get("use", "sig") == "sig":
            try:
                return PyJWK(key_data, algorithm="RS256").key
            except PyJWTError:
                return None
    return None


def _csv(raw: str) -> set[str]:
    return {p.strip() for p in (raw or "").split(",") if p.strip()}


def _roles(payload: dict[str, Any]) -> list[str]:
    roles = payload.get("pc_roles")
    if not isinstance(roles, list):
        roles = (payload.get("realm_access") or {}).get("roles") or []
    return [str(r) for r in roles]


def claims_from_keycloak_payload(payload: dict[str, Any]) -> IdentityClaims:
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="invalid_token")
    roles = _roles(payload)
    azp = str(payload["azp"]) if payload.get("azp") else None
    metadata: dict[str, Any] = {"roles": roles, "groups": payload.get("pc_groups") or []}
    primary = next((r for r in roles if r not in {"mfa_required", "default-roles-porterchain",
                                                   "offline_access", "uma_authorization"}), None)
    if primary:
        metadata["role"] = primary
    email = payload.get("email")
    return IdentityClaims(
        auth_subject=str(sub),
        email=str(email).strip().lower() if email and payload.get("email_verified", True) else None,
        phone=payload.get("phone_number"),
        org_id=payload.get("org_id"),
        org_role=None,
        public_metadata=metadata,
        session_id=payload.get("sid"),
        idp_app=CLIENT_PORTAL.get(azp or ""),
        issuer=str(payload["iss"]) if payload.get("iss") else None,
        authorized_party=azp,
        auth_time=int(payload["auth_time"]) if payload.get("auth_time") is not None else None,
    )


async def verify_keycloak_token(token: str, settings: Settings) -> IdentityClaims:
    issuer = keycloak_issuer(settings)
    jwks_url = keycloak_jwks_url(settings)
    if not issuer or not jwks_url:
        raise HTTPException(status_code=503, detail="auth_not_configured")
    try:
        kid = jwt.get_unverified_header(token).get("kid")
    except PyJWTError as exc:
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    try:
        jwks = await _fetch_jwks(jwks_url)
        key = _key_for(jwks, kid)
        if key is None:  # key rotation: refresh once
            key = _key_for(await _fetch_jwks(jwks_url, force=True), kid)
    except httpx.HTTPError as exc:
        logger.warning("auth_reject reason=jwks_unavailable")
        raise HTTPException(status_code=503, detail="auth_jwks_unavailable") from exc
    if key is None:
        logger.warning("auth_reject reason=invalid_token error=no_matching_jwks_key")
        raise HTTPException(status_code=401, detail="invalid_token")
    audience = (settings.keycloak_audience or "").strip() or None
    try:
        payload = jwt.decode(
            token, key, algorithms=["RS256"], audience=audience, issuer=issuer,
            options={"verify_aud": bool(audience), "require": ["exp", "iat", "sub", "iss"]},
            leeway=_CLOCK_LEEWAY_S,
        )
    except PyJWTError as exc:
        logger.warning("auth_reject reason=invalid_token error=%s", type(exc).__name__)
        raise HTTPException(status_code=401, detail="invalid_token") from exc
    if payload.get("typ") not in (None, "Bearer"):
        raise HTTPException(status_code=401, detail="invalid_token_type")
    parties = _csv(settings.keycloak_allowed_clients)
    azp = payload.get("azp")
    if parties and (not azp or str(azp) not in parties):
        logger.warning("auth_reject reason=authorized_party_mismatch")
        raise HTTPException(status_code=401, detail="invalid_token_azp")
    return claims_from_keycloak_payload(payload)


def production_auth_errors(settings: Settings) -> list[str]:
    """Fail-fast boot checks outside local (names only, never values)."""
    from porterchain_shared.redis_health import is_local_env

    if is_local_env(settings.app_env):
        return []
    errors: list[str] = []
    if settings.auth_dev_bypass:
        errors.append("AUTH_DEV_BYPASS (AUTH_DEV_BYPASS) must be false outside local/development")
    issuer = keycloak_issuer(settings)
    if not issuer:
        errors.append("KEYCLOAK_URL (or KEYCLOAK_ISSUER) required outside local")
    elif not issuer.startswith("https://"):
        errors.append("KEYCLOAK issuer must be https outside local")
    if not (settings.keycloak_audience or "").strip():
        errors.append("KEYCLOAK_AUDIENCE required outside local")
    return errors
