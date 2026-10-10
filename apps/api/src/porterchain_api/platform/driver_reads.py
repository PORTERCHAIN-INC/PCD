"""Read-only Driver rows — other engines must not import admin_models.Driver."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.domain.admin_states import DriverStatus


def get_driver(db: Session, driver_id: str | None) -> Driver | None:
    if not driver_id:
        return None
    return db.get(Driver, driver_id)


def get_driver_by_email(db: Session, email: str) -> Driver | None:
    return db.query(Driver).filter(Driver.email == email).first()


def get_approved_driver_by_email(db: Session, email: str) -> Driver | None:
    return (
        db.query(Driver)
        .filter(Driver.email == email, Driver.status == DriverStatus.APPROVED.value)
        .first()
    )


def list_approved_drivers(db: Session, *, limit: int = 50) -> list[Driver]:
    return (
        db.query(Driver)
        .filter(Driver.status == DriverStatus.APPROVED.value)
        .order_by(Driver.full_name.asc())
        .limit(limit)
        .all()
    )


def get_driver_by_clerk(db: Session, clerk_user_id: str) -> Driver | None:
    return db.query(Driver).filter(Driver.clerk_user_id == clerk_user_id).first()


def list_drivers(db: Session) -> list[Driver]:
    return db.query(Driver).all()
