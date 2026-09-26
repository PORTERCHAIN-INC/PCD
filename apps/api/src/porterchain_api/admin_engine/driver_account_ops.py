"""Driver profile, document decisions, and vehicle writes.

Mixed into AdminDriverService so that module stays within the engine size cap.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.config import Settings
from porterchain_api.domain.customer_goods import persist_vehicle_class

logger = logging.getLogger(__name__)


class DriverAccountOps:
    def attach_vehicle(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        *,
        vehicle_class: str,
        plate_number: str,
        make_model: str | None = None,
        capacity_kg: float | None = None,
        settings: Settings | None = None,
    ) -> Vehicle:
        """D-29: attach vehicle + push Fleetbase when bridge on."""
        driver = self._get_or_raise(db, driver_id)
        plate = plate_number.strip()
        if not plate:
            raise ValueError("plate_number_required")
        self._reject_duplicate_plate(db, plate)
        vehicle = Vehicle(
            driver_id=driver.id,
            vehicle_class=persist_vehicle_class(vehicle_class),
            plate_number=plate,
            make_model=make_model,
            capacity_kg=capacity_kg,
            is_active=True,
        )
        db.add(vehicle)
        self._audit(
            db,
            ctx,
            "driver.vehicle_attached",
            "vehicle",
            driver_id,
            {"plate": plate, "vehicle_class": vehicle.vehicle_class},
        )
        db.commit()
        db.refresh(vehicle)
        if settings:
            self._fleetbase.push_vehicle(db, settings, vehicle)
        return vehicle

    def deactivate_vehicle(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        vehicle_id: str,
        *,
        settings: Settings | None = None,
    ) -> Vehicle:
        """D-29: detach locally and sync inactive state to Fleetbase."""
        self._get_or_raise(db, driver_id)
        vehicle = (
            db.query(Vehicle)
            .filter(Vehicle.id == vehicle_id, Vehicle.driver_id == driver_id)
            .first()
        )
        if not vehicle:
            raise LookupError("vehicle_not_found")
        vehicle.is_active = False
        self._audit(
            db,
            ctx,
            "driver.vehicle_detached",
            "vehicle",
            vehicle_id,
            {"driver_id": driver_id, "is_active": False},
        )
        db.commit()
        db.refresh(vehicle)
        if settings:
            self._fleetbase.push_vehicle(db, settings, vehicle)
        return vehicle

    def decide_document(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        *,
        doc_type: str,
        decision: str,
        reason: str | None = None,
    ) -> Driver:
        from porterchain_api.admin_engine.driver_documents import decide_document
        from porterchain_api.auth.driver_admin_action import run_admin_driver_action

        driver = self._get_or_raise(db, driver_id)
        decide_document(
            db,
            ctx,
            driver,
            doc_type=doc_type,
            decision=decision,
            reason=reason,
            audit=self._audit,
        )
        db.commit()
        db.refresh(driver)
        if decision in {"verified", "rejected"} and getattr(driver, "email", None):
            label = doc_type.replace("_", " ")
            message = (
                f"Your {label} was verified."
                if decision == "verified"
                else f"Your {label} needs a new photo. {(reason or '').strip()}"
            )
            try:
                run_admin_driver_action(
                    db, driver, "email", message, ctx.user.id if ctx.user else None
                )
            except Exception as exc:
                logger.warning("document decision notice failed for %s: %s", driver_id, exc)
        return driver

    def update_profile(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        *,
        full_name: str | None = None,
        phone: str | None = None,
        license_class: str | None = None,
        service_area: str | None = None,
        address: dict | None = None,
        employment_type: str | None = None,
        languages: list[str] | None = None,
        emergency_contact: dict | None = None,
    ) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        if full_name is not None and full_name.strip():
            driver.full_name = full_name.strip()
        if phone is not None:
            driver.phone = phone.strip() or None
        docs = dict(driver.documents or {})
        if license_class is not None:
            docs["license_class"] = license_class.strip() or None
        if service_area is not None:
            docs["service_area"] = service_area.strip() or None
        if address is not None:
            docs["address"] = address
        if employment_type is not None:
            docs["employment_type"] = employment_type.strip() or None
        if languages is not None:
            docs["languages"] = languages
        if emergency_contact is not None:
            docs["emergency_contact"] = emergency_contact
        driver.documents = docs
        self._audit(db, ctx, "driver.profile_updated", "driver", driver_id, {"fields": "identity"})
        db.commit()
        db.refresh(driver)
        return driver

    def update_vehicle(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        vehicle_id: str,
        *,
        vehicle_class: str | None = None,
        plate_number: str | None = None,
        make_model: str | None = None,
        capacity_kg: float | None = None,
        compliance_expires_at=None,
        is_active: bool | None = None,
        settings: Settings | None = None,
    ) -> Vehicle:
        self._get_or_raise(db, driver_id)
        vehicle = (
            db.query(Vehicle).filter(Vehicle.id == vehicle_id, Vehicle.driver_id == driver_id).first()
        )
        if not vehicle:
            raise LookupError("vehicle_not_found")
        if plate_number is not None:
            plate = plate_number.strip()
            if not plate:
                raise ValueError("plate_number_required")
            self._reject_duplicate_plate(db, plate, exclude_id=vehicle.id)
            vehicle.plate_number = plate
        if vehicle_class is not None and vehicle_class.strip():
            vehicle.vehicle_class = persist_vehicle_class(vehicle_class)
        if make_model is not None:
            vehicle.make_model = make_model.strip() or None
        if capacity_kg is not None:
            vehicle.capacity_kg = capacity_kg
        if compliance_expires_at is not None:
            vehicle.compliance_expires_at = compliance_expires_at
        if is_active is not None:
            vehicle.is_active = is_active
        if vehicle.is_active and vehicle.plate_number:
            self._reject_duplicate_plate(db, vehicle.plate_number, exclude_id=vehicle.id)
        self._audit(
            db,
            ctx,
            "driver.vehicle_updated",
            "vehicle",
            vehicle_id,
            {"driver_id": driver_id, "plate": vehicle.plate_number, "is_active": vehicle.is_active},
        )
        db.commit()
        db.refresh(vehicle)
        if settings:
            try:
                self._fleetbase.push_vehicle(db, settings, vehicle)
            except Exception as exc:
                logger.warning("fleetbase vehicle push failed for %s: %s", vehicle_id, exc)
        return vehicle

    def _reject_duplicate_plate(self, db: Session, plate: str, *, exclude_id: str | None = None) -> None:
        from sqlalchemy import func

        query = db.query(Vehicle).filter(
            Vehicle.is_active.is_(True),
            func.lower(Vehicle.plate_number) == plate.lower(),
        )
        if exclude_id:
            query = query.filter(Vehicle.id != exclude_id)
        if query.first():
            raise ValueError("plate_already_active")
