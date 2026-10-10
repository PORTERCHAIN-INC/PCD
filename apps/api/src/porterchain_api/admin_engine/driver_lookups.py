"""Driver row writes owned by admin_engine — reads live in platform.driver_reads."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Driver
from porterchain_api.platform.driver_reads import (
    get_approved_driver_by_email,
    get_driver,
    get_driver_by_clerk,
    get_driver_by_email,
    list_approved_drivers,
    list_drivers,
)

__all__ = [
    "bind_clerk_user_id",
    "get_approved_driver_by_email",
    "get_driver",
    "get_driver_by_clerk",
    "get_driver_by_email",
    "list_approved_drivers",
    "list_drivers",
    "persist_presence",
    "rebind_clerk_by_email",
    "stamp_driver_porterchain_user_id",
]


def stamp_driver_porterchain_user_id(
    db: Session, clerk_user_id: str, user_id: str
) -> Driver | None:
    driver = get_driver_by_clerk(db, clerk_user_id)
    if driver and driver.porterchain_user_id != user_id:
        driver.porterchain_user_id = user_id
    return driver


def persist_presence(db: Session, driver: Any, *, is_online: bool) -> Any:
    driver.is_online = is_online
    driver.availability = "online" if is_online else "offline"
    db.commit()
    return driver


def rebind_clerk_by_email(db: Session, email: str, clerk_id: str) -> bool:
    from porterchain_api.auth.email_identity import emails_match

    row = db.query(Driver).filter(Driver.email == email).first()
    if not row or not emails_match(getattr(row, "email", None), email):
        return False
    if row.clerk_user_id == clerk_id:
        return False
    taken = db.query(Driver).filter(Driver.clerk_user_id == clerk_id).first()
    if taken and taken.id != row.id:
        return False
    row.clerk_user_id = clerk_id
    return True


def bind_clerk_user_id(db: Session, driver: Any, clerk_user_id: str) -> Any:
    driver.clerk_user_id = clerk_user_id
    db.commit()
    db.refresh(driver)
    return driver
