"""Admin bounded-context persistence (drivers, staff)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver


class DriverRepository:
    def get_by_id(self, db: Session, driver_id: str) -> Driver | None:
        return db.query(Driver).filter(Driver.id == driver_id).first()

    def list_all(self, db: Session, *, limit: int = 10_000) -> list[Driver]:
        return db.query(Driver).order_by(Driver.created_at.desc()).limit(limit).all()


class AdminUserRepository:
    def get_by_id(self, db: Session, user_id: str) -> AdminUser | None:
        return db.query(AdminUser).filter(AdminUser.id == user_id).first()

    def get_by_subject(self, db: Session, auth_subject: str) -> AdminUser | None:
        return db.query(AdminUser).filter(AdminUser.auth_subject == auth_subject).first()
