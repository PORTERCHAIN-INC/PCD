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
        entry = self._document_entry(body, ctx)
        files.append(entry)
        docs["files"] = files
        # Mirror into portal keyed schema so driver app sees the upload (D-25).
        portal_key = self._portal_doc_key(body.doc_type)
        if portal_key:
            docs[portal_key] = {
                "status": "pending_review",
                "verified": False,
                "url": body.file_url,
                "uploaded_at": entry["uploaded_at"],
                "reference_number": body.reference_number,
                "expires_at": entry.get("expires_at"),
                "notes": body.notes,
            }
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

    @staticmethod
    def _portal_doc_key(doc_type: str) -> str | None:
        raw = (doc_type or "").lower().strip()
        mapping = {
            "license": "license",
            "driver_license": "license",
            "drivers_license": "license",
            "insurance": "insurance",
            "insurance_certificate": "insurance",
            "vehicle_registration": "vehicle_registration",
            "vehicle_reg": "vehicle_registration",
            "registration": "vehicle_registration",
            "background_check": "background_check",
        }
        return mapping.get(raw)

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
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
        if settings:
            for vehicle in driver.vehicles:
                if vehicle.is_active:
                    self._fleetbase.push_vehicle(db, settings, vehicle)
            self._fleetbase.push_driver(db, settings, driver)
        return driver

    def suspend_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Suspend locally. Returns (driver, fleetbase_sync_warning)."""
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
        # Fleetbase owns live online state — take the driver offline there too.
        # Local suspension stands; surface Fleetbase failure to Admin (D-15).
        fleetbase_sync_warning: str | None = None
        if settings and driver.fleetbase_driver_id:
            try:
                from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

                ok = get_fleetbase_integration(settings).toggle_driver_online(
                    driver.fleetbase_driver_id, online=False
                )
                if not ok:
                    fleetbase_sync_warning = "fleetbase_offline_failed"
                    logger.warning("fleetbase offline push returned false for driver %s", driver_id)
            except Exception as exc:
                fleetbase_sync_warning = "fleetbase_offline_failed"
                logger.warning("fleetbase offline push failed for driver %s: %s", driver_id, exc)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
        return driver, fleetbase_sync_warning

    def deactivate_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Explicit deactivate alias — same effect as suspend (D-30)."""
        return self.suspend_driver(db, ctx, driver_id, settings)

    def reject_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Reject an application / permanently bar from assignable pool (D-30)."""
        driver = self._get_or_raise(db, driver_id)
        driver.status = DriverStatus.REJECTED.value
        driver.is_online = False
        driver.availability = "offline"
        self._audit(db, ctx, "driver.rejected", "driver", driver_id, {})
        emit_event(
            db,
            event_type=E.DRIVER_REJECTED,
            aggregate_type="driver",
            aggregate_id=driver_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(driver)
        fleetbase_sync_warning: str | None = None
        if settings and driver.fleetbase_driver_id:
            try:
                from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

                ok = get_fleetbase_integration(settings).toggle_driver_online(
                    driver.fleetbase_driver_id, online=False
                )
                if not ok:
                    fleetbase_sync_warning = "fleetbase_offline_failed"
            except Exception as exc:
                fleetbase_sync_warning = "fleetbase_offline_failed"
                logger.warning("fleetbase offline push failed on reject %s: %s", driver_id, exc)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
        return driver, fleetbase_sync_warning

    def rehire_driver(
        self, db: Session, ctx: AdminContext, driver_id: str
    ) -> Driver:
        """Move REJECTED/SUSPENDED back to PENDING for re-review (D-30)."""
        driver = self._get_or_raise(db, driver_id)
        if driver.status not in {
            DriverStatus.REJECTED.value,
            DriverStatus.SUSPENDED.value,
        }:
            raise ValueError("driver_not_rehirable")
        driver.status = DriverStatus.PENDING.value
        driver.is_online = False
        self._audit(db, ctx, "driver.rehired", "driver", driver_id, {})
        emit_event(
            db,
            event_type=E.DRIVER_REHIRED,
            aggregate_type="driver",
            aggregate_id=driver_id,
            actor_type="admin",
            actor_id=ctx.user.id,
        )
        db.commit()
        db.refresh(driver)
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
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
            self._sync_portal_doc_status(driver, "license", verified=license_verified)
        if medical_transport_certified is not None:
            driver.medical_transport_certified = medical_transport_certified
        if insurance_verified is not None:
            driver.insurance_verified = insurance_verified
            self._sync_portal_doc_status(driver, "insurance", verified=insurance_verified)
        if vehicle_verified is not None:
            driver.vehicle_verified = vehicle_verified
            self._sync_portal_doc_status(driver, "vehicle_registration", verified=vehicle_verified)
        if background_check_status:
            driver.background_check_status = background_check_status
            passed = background_check_status.lower() in {"passed", "cleared", "approved"}
            self._sync_portal_doc_status(
                driver,
                "background_check",
                verified=passed,
                status="verified" if passed else background_check_status.lower(),
            )
        db.commit()
        db.refresh(driver)
        return driver

    @staticmethod
    def _sync_portal_doc_status(
        driver: Driver,
        portal_key: str,
        *,
        verified: bool,
        status: str | None = None,
    ) -> None:
        """Keep portal keyed docs (license/insurance/…) in sync with Admin verify toggles (D-25)."""
        docs = dict(driver.documents or {})
        entry = docs.get(portal_key)
        if not isinstance(entry, dict):
            entry = {}
        entry["verified"] = verified
        entry["status"] = status or ("verified" if verified else "pending_review")
        docs[portal_key] = entry
        # Also stamp matching Admin files[] entries when present.
        files = list(docs.get("files") or [])
        aliases = {
            "license": {"license", "driver_license", "drivers_license"},
            "insurance": {"insurance", "insurance_certificate"},
            "vehicle_registration": {"vehicle_registration", "vehicle_reg", "registration"},
            "background_check": {"background_check"},
        }.get(portal_key, {portal_key})
        updated_files = []
        for f in files:
            if not isinstance(f, dict):
                updated_files.append(f)
                continue
            doc_type = str(f.get("doc_type") or "").lower()
            if doc_type in aliases or any(a in doc_type for a in aliases):
                f = {**f, "status": entry["status"], "verified": verified}
            updated_files.append(f)
        docs["files"] = updated_files
        driver.documents = docs

    def list_payouts(self, db: Session, driver_id: str) -> list[DriverPayout]:
        return (
            db.query(DriverPayout)
            .filter(DriverPayout.driver_id == driver_id)
            .order_by(DriverPayout.created_at.desc())
            .all()
        )

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
        vehicle = Vehicle(
            driver_id=driver.id,
            vehicle_class=vehicle_class.strip() or "cargoVan",
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
            "status": "pending_review",
            "verified": False,
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
