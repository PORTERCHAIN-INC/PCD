"""Request-scoped auth prepare — UserSync + principal resolve once per Clerk subject."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.user_models import PorterchainUser

_SYNC_CACHE = "_auth_sync_users"
_PRINCIPAL_CACHE = "_auth_principals"


def prepare_user_from_claims(db: Session, claims: ClerkClaims) -> PorterchainUser:
    """Run UserSync once per request/clerk_user_id."""
    from porterchain_api.auth.user_sync_service import UserSyncService

    cache: dict[str, PorterchainUser] = db.info.setdefault(_SYNC_CACHE, {})
    key = claims.clerk_user_id or ""
    if key in cache:
        return cache[key]
    user = UserSyncService().sync(db, claims)
    cache[key] = user
    return user


def resolve_principal_cached(
    db: Session,
    identity: AuthenticatedIdentity,
) -> CurrentPrincipal:
    """Resolve CurrentPrincipal once per request/subject."""
    from porterchain_api.auth.principal_resolution_service import (
        PrincipalResolutionService,
    )

    cache: dict[str, CurrentPrincipal] = db.info.setdefault(_PRINCIPAL_CACHE, {})
    key = identity.subject or ""
    if key in cache:
        return cache[key]
    principal = PrincipalResolutionService().resolve(db, identity)
    cache[key] = principal
    return principal


def invalidate_auth_prepare(db: Session, clerk_user_id: str | None = None) -> None:
    """Clear prepare caches after persona mutations."""
    if clerk_user_id is None:
        db.info.pop(_SYNC_CACHE, None)
        db.info.pop(_PRINCIPAL_CACHE, None)
        return
    sync = db.info.get(_SYNC_CACHE)
    if sync:
        sync.pop(clerk_user_id, None)
    principals = db.info.get(_PRINCIPAL_CACHE)
    if principals:
        principals.pop(clerk_user_id, None)
