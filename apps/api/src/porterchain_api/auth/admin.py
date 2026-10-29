"""Resolve admin staff context from a Keycloak ``pc-admin`` access token."""

import logging
from typing import Annotated, Any

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_engine.staff_lookups import ensure_dev_admin, get_admin_user
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.keycloak_staff import (
    admin_claims_from_bearer,
    admin_user_for_claims,
    looks_like_jwt,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger("porterchain.auth.admin")


async def get_admin_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_role: Annotated[str | None, Header()] = None,
) -> AdminContext:
    """Keycloak ``pc-admin`` bearer (MFA in the realm flow); Bearer ``dev`` in dev only."""
    from porterchain_api.platform.admin_ip_allowlist import enforce as enforce_ip_allowlist

    (await run_in_threadpool(lambda: enforce_ip_allowlist(request, db)))

    if allow_auth_dev_bypass(settings) and (not authorization or authorization == "Bearer dev"):
        return _tag_actor(request, (await run_in_threadpool(lambda: _admin_from_dev_bypass(db, settings, x_admin_role))))

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing_bearer_token")
    token = authorization.removeprefix("Bearer ").strip()
    if token == "dev":
        raise HTTPException(status_code=401, detail="dev_bypass_disabled")
    if not looks_like_jwt(token):
        raise HTTPException(status_code=401, detail="invalid_token")

    claims = await admin_claims_from_bearer(token, settings)
    try:
        request.state.admin_claims = claims
    except Exception:  # noqa: BLE001
        pass
    return _tag_actor(request, (await run_in_threadpool(lambda: _admin_from_keycloak(db, claims, settings, x_admin_role))))


def _admin_from_keycloak(db: Session, claims: Any, settings: Settings, x_admin_role: str | None) -> AdminContext:
    user = admin_user_for_claims(db, claims)
    if not _staff_identity_current(user):
        from porterchain_api.admin_engine.staff_accounts import ensure_staff_identity

        ensure_staff_identity(db, user)
        db.refresh(user)
    return _finish_admin_context(db, user, settings, x_admin_role)


def _admin_from_dev_bypass(
    db: Session,
    settings: Settings,
    x_admin_role: str | None,
) -> AdminContext:
    """API tooling path (Bearer ``dev``) — resolves Local Super Admin via Staff IdP identity.

    Development only; the admin UI signs in through Keycloak like production.
    """
    from porterchain_api.admin_engine.staff_lookups import ensure_local_super_admin

    user = ensure_local_super_admin(db)
    return _finish_admin_context(db, user, settings, x_admin_role)


def _staff_identity_current(user: Any) -> bool:
    """Already bound to ``staff:{id}`` with platform#portal → skip the per-request reconcile.

    Reconciling on every request rewrote this user's SpiceDB tuples on every API call
    (slow, and racy with parallel requests). Role changes re-sync via
    ``sync_authz_after_persona_mutation``; a missing portal edge still self-heals here.
    """
    if not user.porterchain_user_id or str(user.clerk_user_id or "") != f"staff:{user.id}":
        return False
    try:
        return _check_platform(user.porterchain_user_id, "portal")
    except HTTPException:
        return False


def _check_platform(subject_id: str, permission: str) -> bool:
    """SpiceDB platform Check with one retry; outage → 503 (never a false 403)."""
    from porterchain_api.authz.client import get_authz_client
    from porterchain_api.authz.tuples import PLATFORM_ID

    client = get_authz_client()
    last: Exception | None = None
    for _ in range(2):
        try:
            return client.check(
                resource_type="platform",
                resource_id=PLATFORM_ID,
                permission=permission,
                subject_id=subject_id,
            )
        except Exception as exc:  # noqa: BLE001
            last = exc
    logger.warning("authz_check_unavailable permission=%s err=%s", permission, type(last).__name__)
    raise HTTPException(status_code=503, detail="authz_unavailable")


def _finish_admin_context(
    db: Session,
    user: Any,
    settings: Settings,
    x_admin_role: str | None,
) -> AdminContext:
    subject_id = user.porterchain_user_id
    if not subject_id:
        raise HTTPException(status_code=403, detail="admin_assignment_missing")

    if not _check_platform(subject_id, "portal"):
        raise HTTPException(status_code=403, detail="admin_assignment_missing")

    role = parse_admin_role(
        (x_admin_role if allow_auth_dev_bypass(settings) else None) or user.role
    )
    return AdminContext(user=user, role=role)


def _tag_actor(request, ctx: AdminContext) -> AdminContext:
    try:
        request.state.audit_actor = f"admin:{ctx.user.id}"
    except Exception:  # noqa: BLE001
        pass
    return ctx


_ensure_dev_admin = ensure_dev_admin
