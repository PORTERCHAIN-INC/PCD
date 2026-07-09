"""Admin bounded-context persistence (drivers, staff)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import AdminUser, Driver


class DriverRepository:
    def get_by_id(self, db: Session, driver_id: str) -> Driver | None:
        return db.query(Driver).filter(Driver.id == driver_id).first()

    def list_online(self, db: Session, *, limit: int = 200) -> list[Driver]:
        return (
            db.query(Driver)
            .filter(Driver.is_online.is_(True))
            .order_by(Driver.updated_at.desc())
            .limit(limit)
            .all()
        )

    def list_all(self, db: Session, *, limit: int = 10_000) -> list[Driver]:
        return db.query(Driver).order_by(Driver.created_at.desc()).limit(limit).all()


class AdminUserRepository:
    def get_by_id(self, db: Session, user_id: str) -> AdminUser | None:
        return db.query(AdminUser).filter(AdminUser.id == user_id).first()

    def get_by_clerk_id(self, db: Session, clerk_user_id: str) -> AdminUser | None:
        return db.query(AdminUser).filter(AdminUser.clerk_user_id == clerk_user_id).first()

    def first_active(self, db: Session) -> AdminUser | None:
        return db.query(AdminUser).filter(AdminUser.is_active.is_(True)).first()
