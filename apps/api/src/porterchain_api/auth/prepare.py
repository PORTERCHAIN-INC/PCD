"""Request-scoped auth prepare — UserSync + principal resolve once per Keycloak subject."""

from __future__ import annotations

import threading
import time

from sqlalchemy.orm import Session

from porterchain_api.auth.claims import IdentityClaims
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.user_models import PorterchainUser

_SYNC_CACHE = "_auth_sync_users"
_PRINCIPAL_CACHE = "_auth_principals"

# One full UserSync (row locks + SpiceDB write) per subject. Parallel driver
# job polls were each taking that lock and holding a pooled connection until
# the 10-connection production pool made session-context wait past 12s.
_PREPARE_REUSE_S = 20.0
_PREPARE_LOCK_WAIT_S = 3.0
_PREPARE_GUARD = threading.Lock()
_PREPARE_LOCKS: dict[str, threading.Lock] = {}
_PREPARED: dict[str, tuple[float, str]] = {}


def _subject_lock(key: str) -> threading.Lock:
    with _PREPARE_GUARD:
        lock = _PREPARE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _PREPARE_LOCKS[key] = lock
        return lock


def _forget_prepared(auth_subject: str | None) -> None:
    with _PREPARE_GUARD:
        if auth_subject is None:
            _PREPARED.clear()
            return
        _PREPARED.pop(auth_subject, None)


def _reuse_prepared(db: Session, key: str) -> PorterchainUser | None:
    with _PREPARE_GUARD:
        hit = _PREPARED.get(key)
    if hit is None or time.monotonic() - hit[0] >= _PREPARE_REUSE_S:
        return None
    user = db.get(PorterchainUser, hit[1])
    if user is None or user.auth_subject != key:
        _forget_prepared(key)
        return None
    return user


def prepare_user_from_claims(db: Session, claims: IdentityClaims) -> PorterchainUser:
    """Run UserSync once per request, and at most once per subject per 20s.

    The cross-request reuse is taken before the first query so waiters do not
    check out a pooled connection while another request syncs the same subject.
    """
    from porterchain_api.auth.user_sync_service import UserSyncService

    cache: dict[str, PorterchainUser] = db.info.setdefault(_SYNC_CACHE, {})
    key = claims.auth_subject or ""
    if key in cache:
        return cache[key]
    if not key:
        user = UserSyncService().sync(db, claims)
        cache[key] = user
        return user

    lock = _subject_lock(key)
    acquired = lock.acquire(timeout=_PREPARE_LOCK_WAIT_S)
    try:
        reused = _reuse_prepared(db, key)
        if reused is not None:
            cache[key] = reused
            return reused
        if not acquired:
            # Another request is already syncing this subject. Starting a second
            # sync would take another pooled connection and the same row locks.
            from fastapi import HTTPException

            raise HTTPException(status_code=503, detail="db_unavailable")
        user = UserSyncService().sync(db, claims)
        cache[key] = user
        with _PREPARE_GUARD:
            _PREPARED[key] = (time.monotonic(), user.id)
        return user
    finally:
        if acquired:
            lock.release()


def resolve_principal_cached(
    db: Session,
    identity: AuthenticatedIdentity,
) -> CurrentPrincipal:
    """Resolve CurrentPrincipal once per request/subject."""
    from porterchain_api.auth.principal_resolution_service import PrincipalResolutionService

    cache: dict[str, CurrentPrincipal] = db.info.setdefault(_PRINCIPAL_CACHE, {})
    key = identity.subject or ""
    if key in cache:
        return cache[key]
    principal = PrincipalResolutionService().resolve(db, identity)
    cache[key] = principal
    return principal


def invalidate_auth_prepare(db: Session, auth_subject: str | None = None) -> None:
    """Clear prepare caches after persona mutations."""
    _forget_prepared(auth_subject)
    if auth_subject is None:
        db.info.pop(_SYNC_CACHE, None)
        db.info.pop(_PRINCIPAL_CACHE, None)
        return
    sync = db.info.get(_SYNC_CACHE)
    if sync:
        sync.pop(auth_subject, None)
    principals = db.info.get(_PRINCIPAL_CACHE)
    if principals:
        principals.pop(auth_subject, None)
