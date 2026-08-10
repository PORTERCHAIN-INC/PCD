"""Resolve admin staff context from staff IdP session (Clerk JWT retired for admin)."""

from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.clerk_identity_provider import _dev_claims
from porterchain_api.auth.clerk import _sync_and_ensure
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.staff_session import (
    STAFF_COOKIE_NAME,
    get_session,
    session_id_from_authorization,
)
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db


async def get_admin_context(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_role: Annotated[str | None, Header()] = None,
) -> AdminContext:
    """Staff IdP session (cookie / ``staff_sess_`` Bearer). Clerk JWT → 401 retired."""
    staff_sid = session_id_from_authorization(authorization) or request.cookies.get(
        STAFF_COOKIE_NAME
    )
    if staff_sid and not _looks_like_clerk_bearer(authorization):
        return _admin_from_staff_session(db, staff_sid, settings, x_admin_role)

    if allow_auth_dev_bypass(settings) and (not authorization or authorization == "Bearer dev"):
        return _admin_from_dev_bypass(db, settings, x_admin_role)

    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        if token == "dev":
            if not allow_auth_dev_bypass(settings):
                raise HTTPException(status_code=401, detail="dev_bypass_disabled")
            return _admin_from_dev_bypass(db, settings, x_admin_role)
        if token.startswith("staff_sess_"):
            return _admin_from_staff_session(
                db, token.removeprefix("staff_sess_").strip(), settings, x_admin_role
            )
        raise HTTPException(status_code=401, detail="admin_clerk_retired_use_staff_idp")

    if staff_sid:
        return _admin_from_staff_session(db, staff_sid, settings, x_admin_role)

    raise HTTPException(status_code=401, detail="missing_bearer_token")


def _looks_like_clerk_bearer(authorization: str | None) -> bool:
    if not authorization or not authorization.startswith("Bearer "):
        return False
    token = authorization.removeprefix("Bearer ").strip()
    return bool(token) and not token.startswith("staff_sess_") and token != "dev"


def _admin_from_dev_bypass(
    db: Session,
    settings: Settings,
    x_admin_role: str | None,
) -> AdminContext:
    """Local CLERK_DEV_BYPASS — ensure a staff-shaped AdminUser without Clerk JWT."""
    claims = _sync_and_ensure(db, _dev_claims())
    user = (
        db.query(AdminUser)
        .filter(AdminUser.clerk_user_id == claims.clerk_user_id)
        .first()
    )
    if not user:
        user = _ensure_dev_admin(db, claims.clerk_user_id, claims.email, x_admin_role)
    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

    ensure_staff_identity(db, user)
    db.refresh(user)
    return _finish_admin_context(db, user, settings, x_admin_role)


def _admin_from_staff_session(
    db: Session,
    session_id: str,
    settings: Settings,
    x_admin_role: str | None,
) -> AdminContext:
    session = get_session(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="staff_session_invalid")

    user = db.query(AdminUser).filter(AdminUser.id == session.admin_user_id).first()
    if not user:
        raise HTTPException(status_code=403, detail="admin_user_not_found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="admin_user_inactive")

    from porterchain_api.admin_engine.staff_idp_service import ensure_staff_identity

    ensure_staff_identity(db, user)
    db.refresh(user)
    return _finish_admin_context(db, user, settings, x_admin_role)


def _finish_admin_context(
    db: Session,
    user: AdminUser,
    settings: Settings,
    x_admin_role: str | None,
) -> AdminContext:
    from porterchain_api.authz.client import get_authz_client
    from porterchain_api.authz.tuples import PLATFORM_ID

    subject_id = user.porterchain_user_id
    if not subject_id:
        raise HTTPException(status_code=403, detail="admin_assignment_missing")

    client = get_authz_client()
    if not client.check(
        resource_type="platform",
        resource_id=PLATFORM_ID,
        permission="portal",
        subject_id=subject_id,
    ):
        raise HTTPException(status_code=403, detail="admin_assignment_missing")

    role = parse_admin_role(
        (x_admin_role if allow_auth_dev_bypass(settings) else None) or user.role
    )
    return AdminContext(user=user, role=role)


def _ensure_dev_admin(
    db: Session,
    clerk_user_id: str,
    clerk_email: str | None,
    role: str | None,
) -> AdminUser:
    from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

    user = db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first()
    if user:
        return user
    email = (clerk_email or "admin@porterchain.com").strip().lower()
    user = AdminUser(
        clerk_user_id=clerk_user_id,
        email=email,
        name="Dev Admin",
        role=role or "super_admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    sync_authz_after_persona_mutation(db, clerk_user_id)
    return user
