"""Driver management per MODULE_BREAKDOWN.md."""

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.admin_models import AdminAuditLog, Driver, DriverPayout, Vehicle
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.booking_engine.fleetbase_sync_service import FleetbaseSyncService
from porterchain_api.config import Settings


class AdminDriverService:
    def __init__(self) -> None:
        self._fleetbase = FleetbaseSyncService()

    def list_drivers(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Driver]:
        q = db.query(Driver)
        if status:
            q = q.filter(Driver.status == status)
        return q.order_by(Driver.created_at.desc()).limit(limit).all()

    def get_driver(self, db: Session, driver_id: str) -> Driver | None:
        return db.query(Driver).filter(Driver.id == driver_id).first()

    def approve_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        driver.status = DriverStatus.APPROVED.value
        self._audit(db, ctx, "driver.approved", "driver", driver_id, {})
        emit_event(
            db,
            event_type=E.DRIVER_APPROVED,
            aggregate_type="driver",
            aggregate_id=driver_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(driver)
        if settings:
            for vehicle in driver.vehicles:
                if vehicle.is_active:
                    self._fleetbase.sync_vehicle(db, settings, vehicle)
            self._fleetbase.sync_driver(db, settings, driver)
        return driver

    def suspend_driver(self, db: Session, ctx: AdminContext, driver_id: str) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        driver.status = DriverStatus.SUSPENDED.value
        driver.is_online = False
        self._audit(db, ctx, "driver.suspended", "driver", driver_id, {})
        emit_event(
            db,
            event_type=E.DRIVER_SUSPENDED,
            aggregate_type="driver",
            aggregate_id=driver_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(driver)
        return driver

    def update_verification(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        *,
        license_verified: bool | None = None,
        insurance_verified: bool | None = None,
        vehicle_verified: bool | None = None,
        background_check_status: str | None = None,
    ) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        if license_verified is not None:
            driver.license_verified = license_verified
        if insurance_verified is not None:
            driver.insurance_verified = insurance_verified
        if vehicle_verified is not None:
            driver.vehicle_verified = vehicle_verified
        if background_check_status:
            driver.background_check_status = background_check_status
        db.commit()
        db.refresh(driver)
        return driver

    def list_payouts(self, db: Session, driver_id: str) -> list[DriverPayout]:
        return (
            db.query(DriverPayout)
            .filter(DriverPayout.driver_id == driver_id)
            .order_by(DriverPayout.created_at.desc())
            .all()
        )

    def list_vehicles(self, db: Session, driver_id: str | None = None) -> list[Vehicle]:
        q = db.query(Vehicle).filter(Vehicle.is_active.is_(True))
        if driver_id:
            q = q.filter(Vehicle.driver_id == driver_id)
        return q.all()

    def _get_or_raise(self, db: Session, driver_id: str) -> Driver:
        driver = self.get_driver(db, driver_id)
        if not driver:
            raise LookupError("driver_not_found")
        return driver

    def _audit(
        self,
        db: Session,
        ctx: AdminContext,
        action: str,
        resource_type: str,
        resource_id: str,
        payload: dict,
    ) -> None:
        db.add(
            AdminAuditLog(
                actor_user_id=ctx.user.id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                payload=payload,
            )
        )
