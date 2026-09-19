"""FastAPI dependencies for unified identity (Phase 3).

Existing portal contexts (get_admin_context, etc.) remain authoritative for those
routers. New code should prefer require_authenticated / require_permission.
"""

from __future__ import annotations

import logging
from typing import Annotated, Callable

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from porterchain_api.auth.claims import ClerkClaims
from porterchain_api.auth.clerk_identity_provider import (
    _dev_claims,
    claims_to_identity,
    get_identity_provider,
)
from porterchain_api.auth.current_principal import CurrentPrincipal
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.identity import AuthenticatedIdentity
from porterchain_api.auth.prepare import prepare_user_from_claims, resolve_principal_cached
from porterchain_api.auth.unified_catalog import UnifiedPermission
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from porterchain_api.unified_identity_models import AccessAuditLog

logger = logging.getLogger("porterchain.security")


def _claims_for_sync(identity: AuthenticatedIdentity) -> ClerkClaims:
    return ClerkClaims(
        clerk_user_id=identity.subject,
        email=identity.email,
        session_id=identity.session_id,
        clerk_app=(identity.adapter_context or {}).get("clerk_app"),
        issuer=identity.issuer,
        authorized_party=identity.authorized_party,
        auth_time=identity.auth_time,
    )


def _record_denial(
    db: Session,
    *,
    actor_user_id: str | None,
    action: str,
    detail: dict,
) -> None:
    """Persist authz denial. Commit so HTTPException rollback does not drop the row."""
    try:
        db.add(
            AccessAuditLog(
                actor_user_id=actor_user_id,
                action=action,
                resource_type="permission",
                resource_id=None,
                outcome="denied",
                detail=detail,
            )
        )
        db.commit()
    except Exception:  # noqa: BLE001 — never fail the request on audit write
        logger.exception("access_audit_write_failed")
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass


def _identity_from_staff_bearer(db: Session, token: str) -> AuthenticatedIdentity:
    """Map ``staff_sess_*`` Redis session → AuthenticatedIdentity (no Clerk JWT)."""
    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity
    from porterchain_api.admin_engine.staff_lookups import get_admin_user
    from porterchain_api.auth.staff_session import STAFF_BEARER_PREFIX, get_session

    session_id = token.removeprefix(STAFF_BEARER_PREFIX).strip()
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="staff_session_invalid")

    user = get_admin_user(db, session.admin_user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=403, detail="admin_user_not_found")

    ensure_staff_identity(db, user)
    db.refresh(user)
    subject = str(user.clerk_user_id or f"staff:{user.id}")
    return AuthenticatedIdentity(
        provider="staff_idp",
        issuer="porterchain:staff",
        subject=subject,
        session_id=session_id,
        email=user.email,
        email_verified=True,
        adapter_context={"staff_admin_user_id": user.id},
    )


async def get_authenticated_identity(
    authorization: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AuthenticatedIdentity:
    """Authenticate bearer token via IdentityProvider. Does not authorize."""
    if allow_auth_dev_bypass(settings) and (not authorization or authorization == "Bearer dev"):
        claims = _dev_claims()
        prepare_user_from_claims(db, claims)
        return claims_to_identity(claims)

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")

    token = authorization.removeprefix("Bearer ").strip()
    if token == "dev" and allow_auth_dev_bypass(settings):
        claims = _dev_claims()
        prepare_user_from_claims(db, claims)
        return claims_to_identity(claims)

    if token.startswith("staff_sess_"):
        return _identity_from_staff_bearer(db, token)

    identity = await get_identity_provider().authenticate_bearer(token, settings)
    prepare_user_from_claims(db, _claims_for_sync(identity))
    return identity


async def require_authenticated(
    identity: Annotated[AuthenticatedIdentity, Depends(get_authenticated_identity)],
    db: Session = Depends(get_db),
) -> CurrentPrincipal:
    """Authenticate + resolve internal user. Suspended/deactivated → 403."""
    return resolve_principal_cached(db, identity)


def require_permission(*needed: UnifiedPermission | str) -> Callable:
    """Dependency factory: allow if principal has any listed permission (deny-by-default)."""

    required = tuple(needed)

    async def _dependency(
        principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
        db: Session = Depends(get_db),
    ) -> CurrentPrincipal:
        if not required:
            return principal
        if any(principal.has_permission(p) for p in required):
            return principal

        missing = [p.value if isinstance(p, UnifiedPermission) else str(p) for p in required]
        logger.info(
            "authz_denied user_id=%s missing_any_of=%s",
            principal.user_id,
            missing,
        )
        _record_denial(
            db,
            actor_user_id=principal.user_id,
            action="permission.denied",
            detail={"missing_any_of": missing, "roles": sorted(r.value for r in principal.roles)},
        )
        raise HTTPException(status_code=403, detail="forbidden")

    return _dependency


def require_all_permissions(*needed: UnifiedPermission | str) -> Callable:
    """Dependency factory requiring every listed permission."""

    required = tuple(needed)

    async def _dependency(
        principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
        db: Session = Depends(get_db),
    ) -> CurrentPrincipal:
        missing = [
            p.value if isinstance(p, UnifiedPermission) else str(p)
            for p in required
            if not principal.has_permission(p)
        ]
        if not missing:
            return principal
        logger.info("authz_denied user_id=%s missing_all=%s", principal.user_id, missing)
        _record_denial(
            db,
            actor_user_id=principal.user_id,
            action="permission.denied",
            detail={"missing": missing, "roles": sorted(r.value for r in principal.roles)},
        )
        raise HTTPException(status_code=403, detail="forbidden")

    return _dependency


def require_organization_scope(organization_id_param: str = "merchant_id") -> Callable:
    """Ensure CurrentPrincipal has organization-scoped assignment for the route org.

    Prefer ``assert_organization_scope`` from route handlers that already resolve
    merchant_id. This factory only works when a matching path/query param is
    available via FastAPI injection (named ``merchant_id`` by default).
    """

    async def _dependency(
        principal: Annotated[CurrentPrincipal, Depends(require_authenticated)],
        db: Session = Depends(get_db),
        merchant_id: Annotated[str | None, Header(alias="X-Merchant-Id")] = None,
    ) -> CurrentPrincipal:
        org_id = merchant_id
        if not org_id:
            return principal
        if principal.has_organization_scope(org_id):
            return principal
        _record_denial(
            db,
            actor_user_id=principal.user_id,
            action="organization_scope.denied",
            detail={"organization_id": org_id, "param": organization_id_param},
        )
        raise HTTPException(status_code=403, detail="organization_scope_denied")

    return _dependency


def assert_organization_scope(principal: CurrentPrincipal, organization_id: str, db: Session) -> None:
    """Deny unless SpiceDB grants organization#portal for this user. Fail closed on Check errors.

    When Postgres membership is present but SpiceDB is stale (common after first login /
    email enrich), reconcile tuples once from profile rows and re-check.
    """
    from porterchain_api.auth.staff_identity import get_porterchain_user
    from porterchain_api.authz.client import get_authz_client

    client = get_authz_client()
    check_error = False
    try:
        allowed = client.check(
            resource_type="organization",
            resource_id=organization_id,
            permission="portal",
            subject_id=principal.user_id,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "spicedb_org_check_failed user_id=%s org=%s", principal.user_id, organization_id
        )
        allowed = False
        check_error = True

    # Stale graph only — never "heal" across a SpiceDB outage (fail closed).
    if (
        not allowed
        and not check_error
        and organization_id in principal.organization_ids
        and principal.user_id
    ):
        try:
            from porterchain_api.authz.tuples import TupleWriter

            user = get_porterchain_user(db, principal.user_id)
            if user:
                TupleWriter().sync_user_from_profiles(db, user)
                db.flush()
                allowed = client.check(
                    resource_type="organization",
                    resource_id=organization_id,
                    permission="portal",
                    subject_id=principal.user_id,
                )
                if allowed:
                    logger.info(
                        "spicedb_org_scope_healed user_id=%s org=%s",
                        principal.user_id,
                        organization_id,
                    )
        except Exception:  # noqa: BLE001
            logger.exception(
                "spicedb_org_scope_heal_failed user_id=%s org=%s",
                principal.user_id,
                organization_id,
            )

    if allowed:
        return
    _record_denial(
        db,
        actor_user_id=principal.user_id,
        action="organization_scope.denied",
        detail={"organization_id": organization_id},
    )
    raise HTTPException(status_code=403, detail="organization_scope_denied")


def assert_self_scope(principal: CurrentPrincipal, profile_id: str, db: Session) -> None:
    """Deny unless SpiceDB grants profile#access (driver or customer). Fail closed on Check errors."""
    from porterchain_api.authz.client import BulkCheckItem, get_authz_client

    client = get_authz_client()
    try:
        results = client.bulk_check(
            [
                BulkCheckItem(
                    resource_type="driver_profile",
                    resource_id=profile_id,
                    permission="access",
                    subject_id=principal.user_id,
                ),
                BulkCheckItem(
                    resource_type="customer_profile",
                    resource_id=profile_id,
                    permission="access",
                    subject_id=principal.user_id,
                ),
            ]
        )
        allowed = any(results)
    except Exception:  # noqa: BLE001
        logger.exception("spicedb_self_check_failed user_id=%s profile=%s", principal.user_id, profile_id)
        allowed = False

    if allowed:
        return
    _record_denial(
        db,
        actor_user_id=principal.user_id,
        action="self_scope.denied",
        detail={"profile_id": profile_id},
    )
    raise HTTPException(status_code=403, detail="self_scope_denied")


def resolve_principal_for_claims(db: Session, claims: ClerkClaims) -> CurrentPrincipal | None:
    """Best-effort CurrentPrincipal for portal contexts; None if not provisioned."""
    if not claims.clerk_user_id:
        return None
    try:
        # Local CLERK_DEV_BYPASS uses synthetic subject ``dev_clerk_user``.
        # Still sync/resolve so merchant/customer portal guards can run.
        prepare_user_from_claims(db, claims)
        return resolve_principal_cached(
            db,
            AuthenticatedIdentity(
                provider="clerk",
                issuer=claims.issuer,
                subject=claims.clerk_user_id,
                email=claims.email,
                email_verified=True,
                session_id=claims.session_id,
            ),
        )
    except HTTPException:
        return None
