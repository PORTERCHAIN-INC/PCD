"""Driver vehicle management."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class VehicleService:
    def get_active_vehicle(self, db: Session, driver_id: str) -> dict | None:
        from porterchain_api.admin_models import Driver

        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        vehicle = self._query_active(db, driver_id)
        if not vehicle:
            return None
        return self._serialize(vehicle)

    def profile_vehicle(self, db: Session, driver: Any) -> dict | None:
        vehicle = self._query_active(db, driver.id)
        if not vehicle:
            return None
        data = self._serialize(vehicle)
        docs = driver.documents or {}
        maintenance = docs.get("vehicle_maintenance") or {}
        if isinstance(maintenance, dict):
            data["maintenance"] = self._normalize_maintenance(maintenance)
        else:
            data["maintenance"] = self._default_maintenance()
        data["photos"] = docs.get("vehicle_photos") if isinstance(docs.get("vehicle_photos"), list) else []
        return data

    def _query_active(self, db: Session, driver_id: str):
        from porterchain_api.admin_models import Vehicle

        return (
            db.query(Vehicle).filter(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True)).first()
        )

    def list_vehicles(self, db: Session, driver_id: str) -> list[dict]:
        from porterchain_api.admin_models import Vehicle

        rows = db.query(Vehicle).filter(Vehicle.driver_id == driver_id).all()
        return [self._serialize(v) for v in rows]

    def update_vehicle(self, db: Session, driver_id: str, vehicle_id: str, **fields: Any) -> dict:
        from porterchain_api.admin_models import Vehicle

        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.id == vehicle_id, Vehicle.driver_id == driver_id)
            .first()
        )
        if not vehicle:
            raise LookupError("vehicle_not_found")
        for key, value in fields.items():
            if value is not None and hasattr(vehicle, key):
                setattr(vehicle, key, value)
        db.flush()
        return self._serialize(vehicle)

    @staticmethod
    def _serialize(vehicle: Any) -> dict:
        return {
            "id": vehicle.id,
            "vehicle_class": vehicle.vehicle_class,
            "plate_number": vehicle.plate_number,
            "make_model": vehicle.make_model,
            "capacity_kg": vehicle.capacity_kg,
            "compliance_expires_at": vehicle.compliance_expires_at.isoformat() if vehicle.compliance_expires_at else None,
            "fleetbase_vehicle_id": vehicle.fleetbase_vehicle_id,
            "is_active": vehicle.is_active,
        }

    @staticmethod
    def _normalize_maintenance(raw: dict) -> dict:
        status = raw.get("status") or "unknown"
        next_due = raw.get("next_service_due")
        if next_due and status == "unknown":
            try:
                due = datetime.fromisoformat(str(next_due).replace("Z", "+00:00"))
                if due.tzinfo is None:
                    due = due.replace(tzinfo=UTC)
                if due < datetime.now(UTC):
                    status = "overdue"
                else:
                    status = "scheduled"
            except ValueError:
                pass
        return {
            "status": status,
            "last_service_at": raw.get("last_service_at"),
            "next_service_due": next_due,
            "odometer_km": raw.get("odometer_km"),
            "notes": raw.get("notes"),
        }

    @staticmethod
    def _default_maintenance() -> dict:
        return {
            "status": "unknown",
            "last_service_at": None,
            "next_service_due": None,
            "odometer_km": None,
            "notes": None,
        }
