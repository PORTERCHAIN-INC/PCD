"""Driver management per MODULE_BREAKDOWN.md."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService

if TYPE_CHECKING:
    from porterchain_api.schemas_admin import DriverCreateRequest, DriverDocumentInput
from porterchain_api.admin_models import AdminAuditLog, Driver, DriverPayout, Vehicle
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.admin_engine import events as E
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.fleetbase_engine.booking_sync_service import BookingSyncService
from porterchain_api.config import Settings


logger = logging.getLogger(__name__)


class AdminDriverService:
    def __init__(self) -> None:
        self._fleetbase = BookingSyncService()

    def list_drivers(self, db: Session, *, status: str | None = None, limit: int = 50) -> list[Driver]:
        q = db.query(Driver)
        if status:
            q = q.filter(Driver.status == status)
        return q.order_by(Driver.created_at.desc()).limit(limit).all()

    def get_driver(self, db: Session, driver_id: str) -> Driver | None:
        return db.query(Driver).filter(Driver.id == driver_id).first()

    def create_driver(
        self,
        db: Session,
        ctx: AdminContext,
        body: DriverCreateRequest,
        settings: Settings | None = None,
    ) -> Driver:
        email = body.email.strip().lower()
        if db.query(Driver).filter(Driver.email == email).first():
            raise ValueError("driver_email_exists")

        docs: dict = {}
        if body.license_class:
            docs["license_class"] = body.license_class
        if body.license_number:
            docs["license_number"] = body.license_number
        if body.service_area:
            docs["service_area"] = body.service_area
        if body.employment_type:
            docs["employment_type"] = body.employment_type
        if body.address:
            docs["address"] = body.address.model_dump(exclude_none=True)
        if body.emergency_contact:
            docs["emergency_contact"] = body.emergency_contact.model_dump(exclude_none=True)
        if body.documents:
            docs["files"] = [self._document_entry(doc, ctx) for doc in body.documents]

        status = DriverStatus.APPROVED.value if body.auto_approve else DriverStatus.PENDING.value
        driver = Driver(
            full_name=body.full_name.strip(),
            email=email,
            phone=body.phone.strip() if body.phone else None,
            status=status,
            documents=docs,
        )
        db.add(driver)
        db.flush()

        if body.vehicle:
            db.add(
                Vehicle(
                    driver_id=driver.id,
                    vehicle_class=body.vehicle.vehicle_class,
                    plate_number=body.vehicle.plate_number.strip(),
                    make_model=body.vehicle.make_model,
                    capacity_kg=body.vehicle.capacity_kg,
                    compliance_expires_at=body.vehicle.compliance_expires_at,
                )
            )

        self._audit(
            db,
            ctx,
            "driver.created",
            "driver",
            driver.id,
            {"email": driver.email, "auto_approve": body.auto_approve},
        )
        emit_event(
            db,
            event_type=E.DRIVER_CREATED,
            aggregate_type="driver",
            aggregate_id=driver.id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(driver)

        if settings and is_clerk_secret_configured(settings, "driver"):
            try:
                InvitationService().invite_driver(db, ctx, settings, driver)
            except Exception as exc:
                logger.warning("driver_clerk_invite_failed: %s", exc)

        if body.auto_approve and settings:
            for vehicle in driver.vehicles:
                if vehicle.is_active:
                    self._fleetbase.push_vehicle(db, settings, vehicle)
            self._fleetbase.push_driver(db, settings, driver)

        return driver

    def add_document(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        body: DriverDocumentInput,
    ) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        docs = dict(driver.documents or {})
        files = list(docs.get("files") or [])
        files.append(self._document_entry(body, ctx))
        docs["files"] = files
        driver.documents = docs
        self._audit(
            db,
            ctx,
            "driver.document_added",
            "driver",
            driver_id,
            {"doc_type": body.doc_type, "label": body.label},
        )
        db.commit()
        db.refresh(driver)
        return driver

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
                    self._fleetbase.push_vehicle(db, settings, vehicle)
            self._fleetbase.push_driver(db, settings, driver)
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
        medical_transport_certified: bool | None = None,
        insurance_verified: bool | None = None,
        vehicle_verified: bool | None = None,
        background_check_status: str | None = None,
    ) -> Driver:
        driver = self._get_or_raise(db, driver_id)
        if license_verified is not None:
            driver.license_verified = license_verified
        if medical_transport_certified is not None:
            driver.medical_transport_certified = medical_transport_certified
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

    def _document_entry(self, body: DriverDocumentInput, ctx: AdminContext) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "doc_type": body.doc_type,
            "label": body.label or body.doc_type.replace("_", " ").title(),
            "file_url": body.file_url,
            "reference_number": body.reference_number,
            "expires_at": body.expires_at.isoformat() if body.expires_at else None,
            "notes": body.notes,
            "uploaded_at": datetime.now(UTC).isoformat(),
            "uploaded_by": ctx.user.id if ctx.user else None,
        }

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
