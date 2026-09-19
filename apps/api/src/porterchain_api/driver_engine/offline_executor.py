"""Replay queued driver offline actions through DriverPlatform services."""

from __future__ import annotations

from typing import Any

from porterchain_driver import DriverPlatform
from porterchain_driver.offline import ConflictSkip


class DriverOfflineExecutor:
    """Executes queued offline actions — delegates to application services only."""

    def __init__(self, platform: DriverPlatform | None = None) -> None:
        self._platform = platform or DriverPlatform()

    def execute(self, db: Any, driver: Any, action_type: str, payload: dict, *, fleetbase_bridge: Any = None) -> None:
        action = action_type.lower()
        if action == "arrive_stop":
            self._platform.stops.arrive_stop(
                db, driver, payload["stop_id"], fleetbase_bridge=fleetbase_bridge
            )
            return
        if action == "deliver_stop":
            self._platform.stops.deliver_stop(
                db, driver, payload["stop_id"], fleetbase_bridge=fleetbase_bridge
            )
            return
        if action == "location":
            self._platform.location.record_ping(
                db,
                driver,
                lat=float(payload["lat"]),
                lng=float(payload["lng"]),
                accuracy_m=payload.get("accuracy_m"),
                heading=payload.get("heading"),
                speed_mps=payload.get("speed_mps"),
                recorded_at=payload.get("recorded_at"),
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "pod_photo":
            self._platform.pod.capture_photo(
                db,
                driver,
                payload["stop_id"],
                file_url=payload["file_url"],
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "camera_upload":
            self._platform.pod.capture_photo(
                db,
                driver,
                payload["stop_id"],
                file_url=payload["file_url"],
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "pod_signature":
            self._platform.pod.capture_signature(
                db,
                driver,
                payload["stop_id"],
                signature_data=payload["signature_data"],
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "pod_barcode":
            self._platform.pod.capture_barcode(
                db,
                driver,
                payload["stop_id"],
                barcode=payload["barcode"],
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "pod_complete":
            result = self._platform.pod.complete_pod(
                db,
                driver,
                payload["stop_id"],
                otp=payload.get("otp"),
                fleetbase_bridge=fleetbase_bridge,
            )
            if not result.success:
                raise ValueError(result.message or "pod_complete_failed")
            return
        if action == "availability":
            mode = payload.get("mode")
            if mode:
                self._platform.shift.set_availability(
                    db, driver, str(mode), fleetbase_bridge=fleetbase_bridge
                )
            else:
                self._platform.availability.set_online(
                    db, driver, online=bool(payload.get("online")), fleetbase_bridge=fleetbase_bridge
                )
            return
        if action == "shift_start":
            self._platform.shift.start_shift(db, driver, fleetbase_bridge=fleetbase_bridge)
            return
        if action == "shift_end":
            self._platform.shift.end_shift(db, driver, fleetbase_bridge=fleetbase_bridge)
            return
        if action == "shift_break":
            self._platform.shift.start_break(db, driver, fleetbase_bridge=fleetbase_bridge)
            return
        if action == "shift_resume":
            self._platform.shift.resume_shift(db, driver, fleetbase_bridge=fleetbase_bridge)
            return
        if action == "document_upload":
            self._platform.documents.upload_document(
                db,
                driver,
                doc_type=payload["doc_type"],
                file_url=payload["file_url"],
                metadata=payload.get("metadata"),
            )
            return
        if action == "incident":
            self._platform.incidents.report_incident(
                db,
                driver,
                incident_type=payload["incident_type"],
                description=payload["description"],
                order_id=payload.get("order_id"),
                location=payload.get("location"),
                evidence=payload.get("evidence"),
            )
            return
        if action == "support_ticket":
            self._platform.support.create_ticket(
                db,
                driver,
                subject=payload["subject"],
                description=payload.get("description"),
                order_id=payload.get("order_id"),
                priority=payload.get("priority", "normal"),
            )
            return
        if action == "accept_order":
            order_id = payload.get("order_id")
            if not order_id:
                raise ValueError("order_id_required")
            from porterchain_api.booking_models import Order
            from porterchain_api.domain.states import OrderState

            order = db.query(Order).filter(Order.id == order_id, Order.assigned_driver_id == driver.id).first()
            if not order:
                raise LookupError("order_not_found")
            if order.state in {
                OrderState.DRIVER_ACCEPTED.value,
                OrderState.PICKED_UP.value,
                OrderState.IN_TRANSIT.value,
                OrderState.DELIVERED.value,
                OrderState.POD_COMPLETED.value,
            }:
                raise ConflictSkip("order_already_accepted")
            self._platform.availability.accept_assignment(
                db, driver, order_id, fleetbase_bridge=fleetbase_bridge
            )
            return
        if action == "reject_order":
            order_id = payload.get("order_id")
            if not order_id:
                raise ValueError("order_id_required")
            from porterchain_api.booking_models import Order

            order = db.query(Order).filter(Order.id == order_id).first()
            if not order or order.assigned_driver_id != driver.id:
                raise ConflictSkip("order_no_longer_assigned")
            self._platform.availability.reject_assignment(
                db,
                driver,
                order_id,
                reason=payload.get("reason", ""),
                fleetbase_bridge=fleetbase_bridge,
            )
            return
        if action == "generate_otp":
            order_id = payload.get("order_id")
            if not order_id:
                raise ValueError("order_id_required")
            self._platform.pod.generate_otp(db, driver, order_id)
            return
        if action == "otp_verify":
            order_id = payload.get("order_id")
            otp = payload.get("otp")
            if not order_id or not otp:
                raise ValueError("order_id_and_otp_required")
            if not self._platform.pod.verify_otp(db, order_id, str(otp)):
                raise ValueError("invalid_otp")
            return
        if action in {"optimize_route", "optimize"}:
            # Offline intent: on reconnect auto-apply (preview=False). Online UX
            # still uses Preview→Accept; this path is reconnect-only.
            self._platform.jobs.optimize_route(
                db,
                driver,
                preview=bool(payload.get("preview", False)),
            )
            return
        raise ValueError(f"unsupported_offline_action:{action_type}")
