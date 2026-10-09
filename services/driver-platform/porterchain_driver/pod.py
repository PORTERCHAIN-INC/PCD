"""Proof of delivery — OTP, photo, barcode, signature."""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING, Any

from porterchain_driver.types import PodCaptureResult

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ProofOfDeliveryService:
    def generate_otp(self, db: Session, driver: Any, order_id: str,
    ) -> str:
        from porterchain_api.booking_models import Order

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
        if order.assigned_driver_id != driver.id:
            raise PermissionError("order_not_assigned_to_driver")
        otp = f"{secrets.randbelow(900000) + 100000:06d}"
        from porterchain_api.driver_models import DriverStopMeta

        meta_row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
        if not meta_row:
            meta_row = DriverStopMeta(order_id=order_id, driver_id=order.assigned_driver_id or "", meta={})
            db.add(meta_row)
        stop_meta = dict(meta_row.meta or {})
        stop_meta["delivery_otp_hash"] = hashlib.sha256(otp.encode()).hexdigest()
        meta_row.meta = stop_meta
        db.flush()
        return otp

    def verify_otp(self, db: Session, order_id: str, otp: str,
    ) -> bool:
        from porterchain_api.driver_models import DriverStopMeta

        meta_row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
        if not meta_row:
            return False
        expected = (meta_row.meta or {}).get("delivery_otp_hash")
        if not expected:
            return False
        return hashlib.sha256(otp.encode()).hexdigest() == expected

    def capture_photo(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        file_url: str,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        self._record_pod(db, order.id, driver.id, "photo", file_url)
        return PodCaptureResult(success=True, proof_type="photo", proof_id=order.id)

    def capture_signature(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        signature_data: str,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        self._record_pod(db, order.id, driver.id, "signature", signature_data[:200])
        return PodCaptureResult(success=True, proof_type="signature", proof_id=order.id)

    def capture_id_check(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        id_type: str,
        name_matches: bool,
        age_verified: bool | None = None,
    ) -> PodCaptureResult:
        """Receiver ID check (pharmacy / merchant id_required). Stores only the document type and
        the yes/no checks — never the ID number, DOB or an image of the ID."""
        allowed = {"drivers_licence", "health_card", "passport", "photo_id_card", "other_government"}
        kind = (id_type or "").strip().lower()
        if kind not in allowed:
            raise ValueError("invalid_id_type")
        if not name_matches:
            raise ValueError("id_name_mismatch")
        order = _order_for_stop(db, driver, stop_id)
        value = f"type={kind};name_match=1"
        if age_verified is not None:
            value += f";age_ok={1 if age_verified else 0}"
        self._record_pod(db, order.id, driver.id, "id_check", value)
        return PodCaptureResult(success=True, proof_type="id_check", proof_id=order.id)

    def capture_barcode(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        barcode: str,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        self._record_pod(db, order.id, driver.id, "barcode", barcode)
        return PodCaptureResult(success=True, proof_type="barcode", proof_id=order.id)

    def complete_pod(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        otp: str | None = None) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        from porterchain_api.booking_engine.compliance_metadata import otp_required_at_delivery
        from porterchain_api.domain.states import OrderState as _OS
        from porterchain_driver.pod_policy import (
            DriverOffDuty,
            assert_on_duty,
            missing_for,
            pod_enforced)

        if (order.state or "").strip() != _OS.POD_COMPLETED.value:
            try:
                assert_on_duty(db, driver)
            except DriverOffDuty:
                return PodCaptureResult(
                    success=False, proof_type="complete", proof_id=None, message="driver_off_duty")
            if pod_enforced():
                missing = missing_for(db, order)
                if missing:
                    return PodCaptureResult(
                        success=False,
                        proof_type="complete",
                        proof_id=None,
                        message="pod_required:" + ",".join(missing))

        code = (otp or "").strip()
        requires_otp = otp_required_at_delivery(getattr(order, "compliance_metadata", None))
        if requires_otp and not code:
            return PodCaptureResult(
                success=False,
                proof_type="otp",
                proof_id=None,
                message="otp_required")
        if code and not self.verify_otp(db, order.id, code):
            return PodCaptureResult(
                success=False,
                proof_type="otp",
                proof_id=None,
                message="invalid_otp")
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_shared.events.catalog import DomainEventType

        payload = {"stop_id": stop_id, "method": "otp" if code else "pod"}
        current = (order.state or "").strip()
        if current != OrderState.POD_COMPLETED.value:
            if current == OrderState.AT_DESTINATION.value:
                try:
                    transition_order_state(
                        db,
                        order,
                        OrderState.DELIVERED,
                        event_type=DomainEventType.PARCEL_DELIVERED,
                        actor_type="driver",
                        actor_id=driver.id,
                        payload=payload)
                except ValueError as exc:
                    return PodCaptureResult(
                        success=False,
                        proof_type="complete",
                        proof_id=order.id,
                        message=str(exc))
            try:
                transition_order_state(
                    db,
                    order,
                    OrderState.POD_COMPLETED,
                    event_type=DomainEventType.PROOF_COMPLETED,
                    actor_type="driver",
                    actor_id=driver.id,
                    payload=payload)
            except ValueError as exc:
                return PodCaptureResult(
                    success=False,
                    proof_type="complete",
                    proof_id=order.id,
                    message=str(exc))
        return PodCaptureResult(
            success=True,
            proof_type="complete",
            proof_id=order.id,
            message="pod_completed")

    def _record_pod(self, db: Session, order_id: str, driver_id: str, proof_type: str, value: str,
    ) -> None:
        from porterchain_api.driver_models import DriverStopMeta

        meta_row = db.query(DriverStopMeta).filter(DriverStopMeta.order_id == order_id).first()
        if not meta_row:
            meta_row = DriverStopMeta(order_id=order_id, driver_id=driver_id, meta={})
            db.add(meta_row)
        meta = dict(meta_row.meta or {})
        proofs = list(meta.get("proofs", []))
        proofs.append({"type": proof_type, "value": value[:500]})
        meta["proofs"] = proofs
        meta_row.meta = meta
        db.flush()


def _order_for_stop(db: Session, driver: Any, stop_id: str):
    from porterchain_api.booking_models import Order

    order_id = stop_id.rsplit("-", 1)[0]
    order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
    if not order:
        raise LookupError("stop_not_found")
    return order
