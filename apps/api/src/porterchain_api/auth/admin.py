"""Resolve admin staff context from Clerk JWT."""

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from typing import Annotated

from porterchain_api.admin_engine.rbac import AdminContext, parse_admin_role
from porterchain_api.admin_models import AdminUser
from porterchain_api.auth.clerk import ClerkClaims, get_clerk_claims
from porterchain_api.config import Settings, get_settings
from porterchain_api.db import get_db


def _link_admin_by_email(db: Session, claims: ClerkClaims) -> AdminUser | None:
    if not claims.email:
        return None
    user = db.query(AdminUser).filter(AdminUser.email == claims.email.lower()).first()
    if not user:
        return None
    if user.clerk_user_id != claims.clerk_user_id and (
        user.clerk_user_id.startswith("pending:") or user.clerk_user_id == "dev_clerk_user"
    ):
        user.clerk_user_id = claims.clerk_user_id
        db.commit()
        db.refresh(user)
    return user


async def get_admin_context(
    claims: Annotated[ClerkClaims, Depends(get_clerk_claims)],
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    x_admin_role: Annotated[str | None, Header()] = None,
) -> AdminContext:
    user = db.query(AdminUser).filter(AdminUser.clerk_user_id == claims.clerk_user_id).first()
    if not user:
        user = _link_admin_by_email(db, claims)
    if not user:
        if settings.clerk_dev_bypass or settings.app_env == "local":
            user = _ensure_dev_admin(db, claims.clerk_user_id, x_admin_role)
        else:
            raise HTTPException(status_code=403, detail="admin_user_not_found")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="admin_user_inactive")

    role = parse_admin_role(x_admin_role or user.role)
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
