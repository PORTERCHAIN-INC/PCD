"""Driver vehicle management."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class VehicleService:
    def get_active_vehicle(self, db: Session, driver_id: str) -> dict | None:
        from porterchain_api.admin_models import Vehicle

        vehicle = (
            db.query(Vehicle).filter(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True)).first()
        )
        if not vehicle:
            return None
        return self._serialize(vehicle)

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
