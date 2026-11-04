"""Identity provider adapter — delegates bearer verification to Keycloak (L36)."""

from __future__ import annotations

import logging


from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.dev import allow_auth_dev_bypass, dev_claims_for, resolve_dev_portal
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.config import Settings

logger = logging.getLogger("porterchain.security")

def _dev_claims(*, portal: str | None = None, path: str = "", header: str | None = None) -> IdentityClaims:
    """Local Bearer ``dev`` — one Keycloak subject per portal, never staff email on merchant/customer."""
    return dev_claims_for(portal or resolve_dev_portal(path=path, header=header))


def claims_to_identity(claims: IdentityClaims) -> AuthenticatedIdentity:
    return AuthenticatedIdentity(
        provider="keycloak",
        issuer=claims.issuer,
        subject=claims.auth_subject,
        session_id=claims.session_id,
        email=claims.email,
        email_verified=True if claims.email else None,
        auth_time=claims.auth_time,
        authorized_party=claims.authorized_party,
        adapter_context={"idp_app": claims.idp_app} if claims.idp_app else None,
    )


async def verify_access_token(
    token: str,
    settings: Settings,
    *,
    portal: str | None = None,
    path: str = "",
    header: str | None = None,
) -> IdentityClaims:
    if token == "dev" and allow_auth_dev_bypass(settings):
        return _dev_claims(portal=portal, path=path, header=header)

    # L36: Keycloak is the only provider; Keycloak JWKS verification removed.
    from porterchain_api.auth.keycloak import verify_keycloak_token

    return await verify_keycloak_token(token, settings)


class KeycloakIdentityProvider:
    """Keycloak adapter implementing IdentityProvider (no Backend API on authenticate)."""

    async def authenticate_bearer(self, token: str, settings: Settings) -> AuthenticatedIdentity:
        claims = await verify_access_token(token, settings)
        return claims_to_identity(claims)


def get_identity_provider() -> KeycloakIdentityProvider:
    return KeycloakIdentityProvider()
