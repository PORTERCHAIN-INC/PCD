"""Clerk IdentityProvider adapter — JWKS verify only; no Backend API on the hot path."""

from __future__ import annotations

import logging

from fastapi import HTTPException
from jose import JWTError, jwk, jwt
import httpx

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_registry import clerk_jwks_urls
from porterchain_api.auth.dev import allow_auth_dev_bypass, dev_claims_for, resolve_dev_portal
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

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


def _csv_set(raw: str) -> set[str]:
    return {part.strip() for part in (raw or "").split(",") if part.strip()}


def _enforce_token_policy(payload: dict, settings: Settings) -> None:
    """Optional iss / azp / aud policy. Empty settings = skip (4-app dual-read era)."""
    issuers = _csv_set(settings.clerk_authorized_issuers)
    if issuers:
        iss = payload.get("iss")
        if not iss or str(iss) not in issuers:
            logger.warning("auth_reject reason=issuer_mismatch")
            raise HTTPException(status_code=401, detail="invalid_token_issuer")

    parties = _csv_set(settings.clerk_authorized_parties)
    if parties:
        azp = payload.get("azp")
        # Clerk may put client id in azp or in aud when single-valued
        candidates = {str(azp)} if azp else set()
        aud = payload.get("aud")
        if isinstance(aud, str):
            candidates.add(aud)
        elif isinstance(aud, list):
            candidates.update(str(a) for a in aud)
        if not candidates.intersection(parties):
            logger.warning("auth_reject reason=authorized_party_mismatch")
            raise HTTPException(status_code=401, detail="invalid_token_azp")


def _claims_from_payload(payload: dict, *, clerk_app: str | None = None) -> ClerkClaims:
    from porterchain_api.auth.email_identity import email_from_jwt_payload

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_token")
    return ClerkClaims(
        clerk_user_id=str(user_id),
        email=email_from_jwt_payload(payload),
        phone=payload.get("phone_number") or payload.get("primary_phone_number"),
        org_id=payload.get("org_id"),
        org_role=payload.get("org_role"),
        public_metadata=payload.get("public_metadata") if isinstance(payload.get("public_metadata"), dict) else None,
        session_id=payload.get("sid"),
        clerk_app=clerk_app,
        issuer=str(payload["iss"]) if payload.get("iss") else None,
        authorized_party=str(payload["azp"]) if payload.get("azp") else None,
        auth_time=int(payload["iat"]) if payload.get("iat") is not None else None,
    )


def _dev_claims(*, portal: str | None = None, path: str = "", header: str | None = None) -> ClerkClaims:
    """Local Bearer ``dev`` — one Clerk subject per portal, never staff email on merchant/customer."""
    return dev_claims_for(portal or resolve_dev_portal(path=path, header=header))


def claims_to_identity(claims: ClerkClaims) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        provider="clerk",
        issuer=claims.issuer,
        subject=claims.clerk_user_id,
        session_id=claims.session_id,
        email=claims.email,
        email_verified=True if claims.email else None,
        auth_time=claims.auth_time,
        authorized_party=claims.authorized_party,
        adapter_context={"clerk_app": claims.clerk_app} if claims.clerk_app else None,
    )


async def verify_clerk_token(
    token: str,
    settings: Settings,
    *,
    portal: str | None = None,
    path: str = "",
    header: str | None = None,
) -> ClerkClaims:
    if token == "dev" and allow_auth_dev_bypass(settings):
        return _dev_claims(portal=portal, path=path, header=header)

    jwks_entries = clerk_jwks_urls(settings)
    if not jwks_entries:
        raise HTTPException(status_code=503, detail="clerk_not_configured")

    audience = (settings.clerk_audience or "").strip() or None
    decode_options = {"verify_aud": bool(audience), "verify_exp": True, "verify_nbf": True}
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
                audience=audience,
                options=decode_options,
            )
            _enforce_token_policy(payload, settings)
            claims = _claims_from_payload(payload, clerk_app=clerk_app)
            # Default Clerk session JWTs omit email — resolve verified primary via Backend API.
            from porterchain_api.auth.email_identity import enrich_claims_with_verified_email

            return enrich_claims_with_verified_email(claims, settings)
        except HTTPException:
            raise
        except JWTError as exc:
            last_error = exc
            continue

    if last_error:
        logger.warning("auth_reject reason=invalid_token")
        raise HTTPException(status_code=401, detail="invalid_token") from last_error
    logger.warning("auth_reject reason=invalid_token")
    raise HTTPException(status_code=401, detail="invalid_token")


class ClerkIdentityProvider:
    """Clerk adapter implementing IdentityProvider (no Backend API on authenticate)."""

    async def authenticate_bearer(self, token: str, settings: Settings) -> AuthenticatedIdentity:
        claims = await verify_clerk_token(token, settings)
        return claims_to_identity(claims)


def get_identity_provider() -> ClerkIdentityProvider:
    return ClerkIdentityProvider()
