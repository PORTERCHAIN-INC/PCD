"""Driver management per MODULE_BREAKDOWN.md."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from porterchain_api.admin_engine.driver_account_ops import DriverAccountOps
from porterchain_api.admin_engine.rbac import AdminContext
from porterchain_api.auth.clerk_registry import is_clerk_secret_configured
from porterchain_api.auth.invitation_service import InvitationService

if TYPE_CHECKING:
    from porterchain_api.schemas_admin import DriverCreateRequest, DriverDocumentInput
from porterchain_api.admin_models import AdminAuditLog, Driver, DriverPayout, Vehicle
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.domain.customer_goods import persist_vehicle_class
from porterchain_api.admin_engine import events as E
from porterchain_api.domain.admin_states import DriverStatus
from porterchain_api.config import Settings


logger = logging.getLogger(__name__)


class AdminDriverService(DriverAccountOps):
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
                    vehicle_class=persist_vehicle_class(body.vehicle.vehicle_class),
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

        return driver

    def provision_pending_from_lead(self, db: Session, ctx: AdminContext, lead) -> Driver:
        """Idempotent PENDING driver. No Clerk invite."""
        existing = db.query(Driver).filter(Driver.crm_lead_id == lead.id).first()
        if existing:
            return existing
        email = (getattr(lead, "email", None) or "").strip().lower()
        if not email:
            raise ValueError("driver_email_required")
        by_email = db.query(Driver).filter(Driver.email == email).first()
        if by_email:
            if not by_email.crm_lead_id:
                by_email.crm_lead_id = lead.id
                db.commit()
            return by_email
        name = getattr(lead, "primary_contact_name", None) or getattr(lead, "company_name", None) or email
        driver = Driver(
            full_name=str(name).strip()[:255],
            email=email,
            phone=getattr(lead, "phone", None) or None,
            status=DriverStatus.PENDING.value,
            crm_lead_id=lead.id,
            documents={},
        )
        db.add(driver)
        db.flush()
        self._audit(db, ctx, "driver.provisioned_from_lead", "driver", driver.id, {"crm_lead_id": lead.id})
        db.commit()
        db.refresh(driver)
        return driver

    def add_document(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        body: DriverDocumentInput,
    ) -> Driver:
        from porterchain_api.admin_engine.driver_documents import add_document as apply_add

        return apply_add(self, db, ctx, driver_id, body)

    @staticmethod
    def _portal_doc_key(doc_type: str) -> str | None:
        from porterchain_api.admin_engine.driver_documents import portal_doc_key

        return portal_doc_key(doc_type)

    def approve_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Approve a driver account. Documents may be filed later."""
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
        warning: str | None = None
        try:
            from porterchain_api.auth.driver_admin_action import run_admin_driver_action

            if getattr(driver, "email", None):
                run_admin_driver_action(
                    db,
                    driver,
                    "email",
                    "You are approved. You can be assigned once license, insurance, and background check are marked.",
                    ctx.user.id if ctx.user else None,
                )
        except Exception as exc:
            logger.warning("driver approve notice failed for %s: %s", driver_id, exc)
        return driver, warning

    def suspend_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Suspend locally. Returns (driver, unused_warning) for call-site compat."""
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
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
        revoke_driver_sessions(driver, settings)
        return driver, None

    def deactivate_driver(
        self, db: Session, ctx: AdminContext, driver_id: str, settings: Settings | None = None
    ) -> tuple[Driver, str | None]:
        """Explicit deactivate alias — same effect as suspend (D-30)."""
        return self.suspend_driver(db, ctx, driver_id, settings)

    def reject_driver(
        self,
        db: Session,
        ctx: AdminContext,
        driver_id: str,
        settings: Settings | None = None,
        reason: str | None = None,
    ) -> tuple[Driver, str | None]:
        """Reject an application / permanently bar from assignable pool (D-30)."""
        driver = self._get_or_raise(db, driver_id)
        driver.status = DriverStatus.REJECTED.value
        driver.is_online = False
        driver.availability = "offline"
        note = (reason or "").strip()
        if note:
            docs = dict(driver.documents or {})
            docs["account_rejection"] = {"reason": note}
            driver.documents = docs
        self._audit(db, ctx, "driver.rejected", "driver", driver_id, {"reason": note or None})
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
        from porterchain_api.auth.authz_sync import sync_authz_after_persona_mutation

        sync_authz_after_persona_mutation(db, driver.clerk_user_id)
        revoke_driver_sessions(driver, settings)
        return driver, None

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
        from porterchain_api.admin_engine.driver_documents import update_verification as apply_verify

        return apply_verify(
            self,
            db,
            ctx,
            driver_id,
            license_verified=license_verified,
            medical_transport_certified=medical_transport_certified,
            insurance_verified=insurance_verified,
            vehicle_verified=vehicle_verified,
            background_check_status=background_check_status,
        )

    @staticmethod
    def _sync_portal_doc_status(
        driver: Driver,
        portal_key: str,
        *,
        verified: bool,
        status: str | None = None,
    ) -> None:
        from porterchain_api.admin_engine.driver_documents import sync_portal_doc_status

        sync_portal_doc_status(driver, portal_key, verified=verified, status=status)

    def list_payouts(self, db: Session, driver_id: str, *, limit: int | None = None) -> list[DriverPayout]:
        q = (
            db.query(DriverPayout)
            .filter(DriverPayout.driver_id == driver_id)
            .order_by(DriverPayout.created_at.desc())
        )
        if limit is not None:
            q = q.limit(limit)
        return q.all()

    def get_payout(self, db: Session, payout_id: str) -> DriverPayout | None:
        return db.get(DriverPayout, payout_id)

    def create_payout(
        self,
        db: Session,
        driver_id: str,
        *,
        amount_cents: int | None = None,
        reference: str | None = None,
        currency: str = "cad",
        commit: bool = False,
    ) -> DriverPayout:
        """Reserve a pending payout and debit wallet. Caller may add wallet ledger then commit."""
        from porterchain_api.driver_engine.wallet_ledger import wallet_balance_cents

        driver = db.get(Driver, driver_id)
        if not driver:
            raise LookupError("driver_not_found")
        balance = wallet_balance_cents(db, driver_id, cached_cents=driver.wallet_balance_cents)
        cents = int(amount_cents) if amount_cents is not None else balance
        if cents <= 0:
            raise ValueError("payout_amount_invalid")
        if cents > balance:
            raise ValueError("insufficient_wallet_balance")
        payout = DriverPayout(
            id=str(uuid.uuid4()),
            driver_id=driver_id,
            amount_cents=cents,
            currency=(currency or "cad").lower(),
            status="pending",
            reference=reference or f"PO-{datetime.now(UTC).strftime('%Y%m%d')}-{driver_id[:8]}",
        )
        db.add(payout)
        if commit:
            db.commit()
            db.refresh(payout)
        else:
            db.flush()
        return payout

    def mark_payout_paid(
        self, db: Session, payout_id: str, *, driver_id: str | None = None
    ) -> DriverPayout:
        payout = self.get_payout(db, payout_id)
        if not payout or (driver_id is not None and payout.driver_id != driver_id):
            raise LookupError("payout_not_found")
        if payout.status == "paid":
            return payout
        if payout.status not in ("pending", "processing"):
            raise ValueError("payout_not_payable")
        payout.status = "paid"
        db.commit()
        db.refresh(payout)
        return payout


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
        from porterchain_api.admin_engine.driver_documents import document_entry

        return document_entry(body, ctx)

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


def revoke_driver_sessions(driver: Driver, settings: Settings | None) -> None:
    """Offboarding: sign the driver out of Clerk everywhere (best effort; API access is
    already blocked by status on every request)."""
    if not driver.clerk_user_id:
        return
    try:
        from porterchain_api.auth.clerk_registry import clerk_client_for_kind
        from porterchain_api.config import get_settings

        n = clerk_client_for_kind(settings or get_settings(), "driver").revoke_sessions(driver.clerk_user_id)
        logger.info("driver_sessions_revoked driver=%s count=%s", driver.id, n)
    except Exception as exc:  # noqa: BLE001
        logger.warning("driver_session_revoke_failed driver=%s: %s", driver.id, exc)
