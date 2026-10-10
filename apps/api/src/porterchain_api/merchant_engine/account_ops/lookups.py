"""Read-only lookups of admin-owned rows (staff users, system config).

Kept apart from the writers in this package: merchant_engine reads these
tables but never writes them (model ownership §3.2.3).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, SystemConfig


def system_config(db: Session, key: str) -> Any:
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row is not None else None


def active_admin(db: Session, admin_id: str) -> Any:
    user = db.get(AdminUser, admin_id)
    return user if user is not None and user.is_active else None


def first_super_admin_emails(db: Session, limit: int = 3) -> list[str]:
    rows = (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True), AdminUser.role == "super_admin")
        .order_by(AdminUser.created_at.asc())
        .limit(limit)
        .all()
    )
    return [u.email for u in rows if u.email]


def active_admins_with_roles(db: Session, roles: tuple[str, ...], *, limit: int = 200) -> list[Any]:
    return (
        db.query(AdminUser)
        .filter(AdminUser.is_active.is_(True), AdminUser.role.in_(roles))
        .order_by(AdminUser.name.asc(), AdminUser.email.asc())
        .limit(limit)
        .all()
    )


def admin_names(db: Session, ids: set[str]) -> dict[str, str]:
    if not ids:
        return {}
    return {
        u.id: (u.name or u.email.split("@")[0]) for u in db.query(AdminUser).filter(AdminUser.id.in_(ids)).all()
    }
