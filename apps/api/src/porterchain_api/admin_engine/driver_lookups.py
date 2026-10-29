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
    db: Session, auth_subject: str, user_id: str
) -> Driver | None:
    driver = get_driver_by_clerk(db, auth_subject)
    if driver and driver.porterchain_user_id != user_id:
        driver.porterchain_user_id = user_id
    return driver


def persist_presence(db: Session, driver: Any, *, is_online: bool) -> Any:
    driver.is_online = is_online
    driver.availability = "online" if is_online else "offline"
    db.commit()
    return driver


def rebind_clerk_by_email(db: Session, email: str, subject_ref: str) -> bool:
    from porterchain_api.auth.email_identity import emails_match

    row = db.query(Driver).filter(Driver.email == email).first()
    if not row or not emails_match(getattr(row, "email", None), email):
        return False
    if row.auth_subject == subject_ref:
        return False
    taken = db.query(Driver).filter(Driver.auth_subject == subject_ref).first()
    if taken and taken.id != row.id:
        return False
    row.auth_subject = subject_ref
    return True


def bind_clerk_user_id(db: Session, driver: Any, auth_subject: str) -> Any:
    driver.auth_subject = auth_subject
    db.commit()
    db.refresh(driver)
    return driver
