"""Resolve admin staff context from Clerk JWT."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.auth.dev import allow_auth_dev_bypass
from porterchain_api.auth.portal_guard import assert_clerk_id_exclusive, require_clerk_app_for_portal
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db


def _admin_by_clerk_id(db: Session, clerk_user_id: str) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first()


async def get_admin_context(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_role: Annotated[str | None, Header()] = None,
) -> AdminContext:
    require_clerk_app_for_portal(claims, settings, "admin")
    assert_clerk_id_exclusive(db, claims, portal="admin", settings=settings)

    user = _admin_by_clerk_id(db, claims.clerk_user_id)
    if not user and allow_auth_dev_bypass(settings):
        user = _ensure_dev_admin(db, claims.clerk_user_id, x_admin_role)
    if not user:
        raise HTTPException(status_code=403, detail="admin_user_not_found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="admin_user_inactive")

    role = parse_admin_role(
        (x_admin_role if allow_auth_dev_bypass(settings) else None) or user.role
    )
    return AdminContext(user=user, role=role)


def _ensure_dev_admin(db: Session, clerk_user_id: str, role: str | None) -> AdminUser:
    user = db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first()
    if user:
        return user
    user = AdminUser(
        clerk_user_id=clerk_user_id,
        email="admin@porterchain.com",
        name="Dev Admin",
        role=role or "super_admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
