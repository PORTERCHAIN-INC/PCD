"""Proof of delivery — OTP, photo, barcode, signature."""

from __future__ import annotations

import hashlib
import secrets
from typing import TYPE_CHECKING, Any

from porterchain_driver.types import PodCaptureResult

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class ProofOfDeliveryService:
    def generate_otp(self, db: Session, order_id: str) -> str:
        from porterchain_api.models import Order

        order = db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise LookupError("order_not_found")
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

    def verify_otp(self, db: Session, order_id: str, otp: str) -> bool:
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
        fleetbase_bridge: Any = None,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        synced = False
        if fleetbase_bridge and order.fleetbase_order_id:
            synced = fleetbase_bridge.upload_pod_photo(order.fleetbase_order_id, file_url)
        self._record_pod(db, order.id, driver.id, "photo", file_url)
        return PodCaptureResult(success=True, proof_type="photo", proof_id=order.id, fleetbase_synced=synced)

    def capture_signature(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        signature_data: str,
        fleetbase_bridge: Any = None,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        synced = False
        if fleetbase_bridge and order.fleetbase_order_id:
            synced = fleetbase_bridge.upload_pod_signature(order.fleetbase_order_id, signature_data)
        self._record_pod(db, order.id, driver.id, "signature", signature_data[:200])
        return PodCaptureResult(success=True, proof_type="signature", proof_id=order.id, fleetbase_synced=synced)

    def capture_barcode(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        barcode: str,
        fleetbase_bridge: Any = None,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        synced = False
        if fleetbase_bridge and order.fleetbase_order_id:
            synced = fleetbase_bridge.upload_pod_barcode(order.fleetbase_order_id, barcode)
        self._record_pod(db, order.id, driver.id, "barcode", barcode)
        return PodCaptureResult(success=True, proof_type="barcode", proof_id=order.id, fleetbase_synced=synced)

    def complete_pod(
        self,
        db: Session,
        driver: Any,
        stop_id: str,
        *,
        otp: str | None = None,
        fleetbase_bridge: Any = None,
    ) -> PodCaptureResult:
        order = _order_for_stop(db, driver, stop_id)
        if otp and not self.verify_otp(db, order.id, otp):
            return PodCaptureResult(success=False, proof_type="otp", proof_id=None, fleetbase_synced=False, message="invalid_otp")
        from porterchain_api.domain.states import OrderState
        from porterchain_api.booking_engine.order_transitions import transition_order_state
        from porterchain_shared.events.catalog import DomainEventType

        transition_order_state(
            db,
            order,
            OrderState.POD_COMPLETED,
            event_type=DomainEventType.PROOF_COMPLETED,
            actor_type="driver",
            actor_id=driver.id,
        )
        return PodCaptureResult(success=True, proof_type="complete", proof_id=order.id, fleetbase_synced=True, message="pod_completed")

    def _record_pod(self, db: Session, order_id: str, driver_id: str, proof_type: str, value: str) -> None:
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
    from porterchain_api.models import Order

    order_id = stop_id.rsplit("-", 1)[0]
    order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
    if not order:
        raise LookupError("stop_not_found")
    return order
