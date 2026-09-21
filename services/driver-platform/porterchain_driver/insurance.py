"""Driver insurance & compliance status."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class InsuranceService:
    def status(self, db: Session, driver: Any) -> dict:
        from porterchain_driver.vehicle import VehicleService

        vehicle = VehicleService().get_active_vehicle(db, driver.id)
        docs = (driver.documents or {}).get("insurance", {})
        expires = docs.get("expires_at")
        expired = False
        if expires:
            try:
                expired = datetime.fromisoformat(expires.replace("Z", "+00:00")) < datetime.now(UTC)
            except ValueError:
                pass
        return {
            "insurance_verified": bool(driver.insurance_verified),
            "vehicle_verified": bool(driver.vehicle_verified),
            "license_verified": bool(driver.license_verified),
            "background_check_status": driver.background_check_status,
            "policy_number": docs.get("policy_number"),
            "provider": docs.get("provider"),
            "expires_at": expires,
            "is_expired": expired,
            "vehicle_compliance_expires_at": vehicle.get("compliance_expires_at") if vehicle else None,
            "compliant": driver.insurance_verified and driver.license_verified and not expired,
            "verified": bool(driver.insurance_verified),
            "status": (
                "expired"
                if expired
                else "verified"
                if driver.insurance_verified
                else "uploaded"
                if docs.get("url") or docs.get("file_url")
                else "not_on_file"
            ),
        }
