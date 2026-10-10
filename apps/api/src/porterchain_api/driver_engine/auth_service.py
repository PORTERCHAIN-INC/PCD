"""Driver authentication — Clerk session only (no Porterchain cookie JWT)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from porterchain_api.platform.driver_reads import (
    get_approved_driver_by_email,
    list_approved_drivers,
)


class DriverAuthService:

    def approved_dev_login(self, db: Session, email: str) -> dict | None:
        driver = get_approved_driver_by_email(db, email.lower().strip())
        if not driver:
            return None
        return {
            "driver_id": driver.id,
            "email": driver.email,
            "full_name": driver.full_name,
            "status": driver.status,
        }

    def list_approved_dev_drivers(self, db: Session, *, limit: int) -> list[dict]:
        return [
            {"driver_id": d.id, "email": d.email, "full_name": d.full_name}
            for d in list_approved_drivers(db, limit=limit)
        ]
