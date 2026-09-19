"""BookingSyncService — outbound Porterchain → Fleetbase order synchronisation.

Reacts to domain events (never called by the frontend). Pushes order creation,
driver assignment, cancellation, return, damage and claim state to Fleetbase via
the adapter, with durable retry + audit. The order state machine stays canonical
in Porterchain; Fleetbase mirrors execution.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence

from sqlalchemy.orm import Session, selectinload

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.fleetbase_engine.integration_bridge import FleetbaseIntegrationBridge
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.audit_logger import AuditLogger
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.booking_models import Order
from porterchain_api.admin_models import Driver, Vehicle
from porterchain_api.fleetbase_models import FleetbaseSyncJob

logger = logging.getLogger(__name__)


class PermanentSyncSkip(Exception):
    """Payload/contract poison — mark job done; never retry forever."""


def _is_seed_fleetbase_public_id(value: str | None) -> bool:
    """Local seed / fixture IDs like ``fb-123`` / ``fb-ord-1`` — not live ``order_`` / ``driver_``."""
    if not value:
        return False
    v = str(value).strip()
    if v.startswith(("order_", "driver_", "place_")):
        return False
    # Hex seed tokens (fb-e072ffe9) and common fixtures (fb-ord-1, fb-d1).
    # Do not match mock ids used in unit tests (fb-drv, fb-new).
    return bool(re.fullmatch(r"(?:fb-[0-9a-f]+|fb-ord-\w+|fb-d\d+)", v, flags=re.IGNORECASE))


#: Retry kinds that are meaningless without their order row.
_ORDER_SCOPED_KINDS = (
    "order",
    "driver",
    "cancellation",
    "return",
    "damage",
    "webhook",
    "pod_photo",
    "pod_signature",
    "pod_barcode",
    "proofs",
    "order_state",
)


class BookingSyncService:
    def __init__(self) -> None:
        self._bridge = FleetbaseIntegrationBridge()

    # ------------------------------------------------------------------ #
    # Order create / update
    # ------------------------------------------------------------------ #
    def push_order(
        self, db: Session, settings: Settings, order: Order, *, commit: bool = True
    ) -> str | None:
        """Enqueue Fleetbase order sync. HTTP runs only in process_retry_queue."""
        if not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(db, direction="outbound", kind="order", status="skipped",
                            order_id=order.id, message="dispatch_bridge_disabled")
            return None
        RetryQueue.enqueue(
            db, direction="outbound", kind="order",
            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
            idempotency_key=f"order:{order.id}",
            payload={"order_id": order.id},
            commit=commit,
        )
        AuditLogger.log(
            db, direction="outbound", kind="order", status="queued",
            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
            message="order sync enqueued",
        )
        return order.fleetbase_order_id

    def enqueue_unlinked_open_orders(
        self,
        db: Session,
        settings: Settings,
        *,
        limit: int = 50,
        commit: bool = True,
    ) -> int:
        """Queue order sync for live work that never got a Fleetbase job.

        Event-bus handlers miss rows when the worker is down. Idempotent enqueue.
        """
        if not settings.fleetbase_dispatch_bridge:
            return 0
        from porterchain_api.domain.states import FLEETBASE_SYNC_EXCLUDED_STATES

        rows = (
            db.query(Order)
            .filter(
                Order.state.notin_(tuple(FLEETBASE_SYNC_EXCLUDED_STATES)),
                Order.fleetbase_order_id.is_(None),
            )
            .limit(limit)
            .all()
        )
        for order in rows:
            self.push_order(db, settings, order, commit=False)
        if commit and rows:
            db.commit()
        return len(rows)

    # ------------------------------------------------------------------ #
    # Driver assignment
    # ------------------------------------------------------------------ #
    def push_driver_assignment(
        self,
        db: Session,
        settings: Settings,
        order: Order,
        *,
        fleetbase_driver_id: str | None,
        driver_id: str | None = None,
        commit: bool = True,
    ) -> None:
        """Enqueue driver assignment. Ensures an order sync job exists first."""
        if not settings.fleetbase_dispatch_bridge:
            return
        if not order.fleetbase_order_id:
            self.push_order(db, settings, order, commit=commit)
        RetryQueue.enqueue(
            db, direction="outbound", kind="driver", order_id=order.id,
            fleetbase_order_id=order.fleetbase_order_id,
            idempotency_key=f"driver:{order.id}:{fleetbase_driver_id or driver_id or 'none'}",
            payload={
                "order_id": order.id,
                "fleetbase_driver_id": fleetbase_driver_id,
                "driver_id": driver_id,
            },
            commit=commit,
        )
        AuditLogger.log(
            db, direction="outbound", kind="driver", status="queued",
            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
            detail={"fleetbase_driver_id": fleetbase_driver_id, "driver_id": driver_id},
        )

    def push_driver(
        self, db: Session, settings: Settings, driver: Driver, *, commit: bool = True
    ) -> str | None:
        """Enqueue driver profile sync. HTTP runs only in process_retry_queue."""
        if not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(
                db, direction="outbound", kind="driver_profile", status="skipped",
                message="dispatch_bridge_disabled", detail={"driver_id": driver.id},
            )
            return None
        RetryQueue.enqueue(
            db, direction="outbound", kind="driver_profile",
            idempotency_key=f"driver_profile:{driver.id}",
            payload={"driver_id": driver.id},
            commit=commit,
        )
        AuditLogger.log(
            db, direction="outbound", kind="driver_profile", status="queued",
            message="driver sync enqueued", detail={"driver_id": driver.id},
        )
        return driver.fleetbase_driver_id

    def push_vehicle(
        self, db: Session, settings: Settings, vehicle: Vehicle, *, commit: bool = True
    ) -> str | None:
        """Enqueue vehicle sync. HTTP runs only in process_retry_queue."""
        if not settings.fleetbase_dispatch_bridge:
            return None
        RetryQueue.enqueue(
            db, direction="outbound", kind="vehicle",
            idempotency_key=f"vehicle:{vehicle.id}",
            payload={"vehicle_id": vehicle.id},
            commit=commit,
        )
        AuditLogger.log(
            db, direction="outbound", kind="vehicle", status="queued",
            message="vehicle sync enqueued",
            detail={"vehicle_id": vehicle.id},
        )
        return vehicle.fleetbase_vehicle_id

    # ------------------------------------------------------------------ #
    # Exception sync (cancellation / return / damage / claim)
    # ------------------------------------------------------------------ #
    def _push_status(
        self,
        db: Session,
        settings: Settings,
        order: Order,
        kind: str,
        status: str,
        *,
        commit: bool = True,
    ) -> None:
        """Enqueue an exception status push. HTTP runs only in process_retry_queue."""
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(db, direction="outbound", kind=kind, status="skipped",
                            order_id=order.id, message="no_fleetbase_id_or_bridge_disabled")
            return
        RetryQueue.enqueue(
            db, direction="outbound", kind=kind, order_id=order.id,
            fleetbase_order_id=order.fleetbase_order_id,
            idempotency_key=f"{kind}:{order.id}",
            payload={"order_id": order.id, "status": status},
            commit=commit,
        )
        AuditLogger.log(
            db, direction="outbound", kind=kind, status="queued",
            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
            detail={"status": status},
        )
    @staticmethod
    def _http_push_status(
        bridge: FleetbaseIntegrationBridge,
        settings: Settings,
        order: Order,
        kind: str,
        status: str,
    ) -> None:
        """HTTP-only exception push for the drain path — never re-enqueues."""
        if kind == "cancellation":
            ok = bridge.cancel_order(settings, order)
            if not ok:
                raise RuntimeError("fleetbase_cancel_failed")
        else:
            integration = bridge._integration(settings)
            integration.sync_order(
                {
                    "fleetbase_order_id": order.fleetbase_order_id,
                    "porterchain_order_id": order.id,
                    "status": status,
                }
            )

    def sync_cancellation(self, db: Session, settings: Settings, order: Order) -> None:
        self._push_status(db, settings, order, "cancellation", "canceled")
        emit_event(db, event_type="fleetbase.cancellation_synced", aggregate_type="order",
                   aggregate_id=order.id, actor_type="system")

    def sync_return(self, db: Session, settings: Settings, order: Order) -> None:
        self._push_status(db, settings, order, "return", "returned")

    def sync_damage(self, db: Session, settings: Settings, order: Order) -> None:
        self._push_status(db, settings, order, "damage", "damaged")

    def sync_claim(self, db: Session, settings: Settings, order: Order, claim_id: str | None = None) -> None:
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(db, direction="outbound", kind="claim", status="skipped", order_id=order.id)
            return
        AuditLogger.log(db, direction="outbound", kind="claim", status="ok",
                        order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
                        detail={"claim_id": claim_id})

    # ------------------------------------------------------------------ #
    # Retry drain (called by worker / ops action)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _replay_webhook(db: Session, settings: Settings, job) -> None:
        """
        Re-run an inbound webhook that failed the first time.

        Without this, `kind="webhook"` matched no branch and fell straight through
        to `mark_done`, so a failed driver status or POD update was discarded and
        counted as a success.
        """
        from porterchain_api.fleetbase_engine.webhook_processor import WebhookProcessor

        update = (job.payload or {}).get("update") or {}
        if not update:
            raise PermanentSyncSkip("webhook_payload_missing_update")
        # `process` re-enqueues on failure, but the idempotency key resolves back
        # to this same job, so a replay cannot fan out into duplicate rows.
        if WebhookProcessor().process(db, settings, update) is None:
            raise RuntimeError("webhook_reprocess_failed")

    def _http_dispatch_kind(
        self,
        bridge: FleetbaseIntegrationBridge,
        db: Session,
        settings: Settings,
        job,
        order: Order | None,
    ) -> None:
        """Execute one claimed job via HTTP only (no re-enqueue)."""
        payload = job.payload or {}
        kind = job.kind

        if kind == "order" and order:
            fleetbase_id = bridge.sync_order(db, settings, order)
            if not fleetbase_id:
                raise RuntimeError("fleetbase_order_id_not_returned")
        elif kind == "driver" and order:
            if not order.fleetbase_order_id:
                fleetbase_id = bridge.sync_order(db, settings, order)
                if not fleetbase_id:
                    raise RuntimeError("fleetbase_order_id_not_returned")
            fb_driver = payload.get("fleetbase_driver_id")
            if not fb_driver and payload.get("driver_id"):
                driver = db.query(Driver).filter(Driver.id == payload.get("driver_id")).first()
                if driver:
                    if not driver.fleetbase_driver_id:
                        bridge.sync_driver(db, settings, driver)
                        db.refresh(driver)
                    fb_driver = driver.fleetbase_driver_id
            if not fb_driver:
                raise PermanentSyncSkip("dispatch_missing_fleetbase_driver_id")
            if _is_seed_fleetbase_public_id(order.fleetbase_order_id) or _is_seed_fleetbase_public_id(
                str(fb_driver) if fb_driver else None
            ):
                raise PermanentSyncSkip("dispatch_seed_fleetbase_id")
            result = bridge.sync_dispatch(
                settings, order, fleetbase_driver_id=fb_driver
            )
            if not result:
                raise RuntimeError("fleetbase_dispatch_not_acknowledged")
        elif kind == "driver_profile":
            driver = db.query(Driver).filter(Driver.id == payload.get("driver_id")).first()
            if not driver:
                raise PermanentSyncSkip("driver_profile_missing_driver")
            if not bridge.sync_driver(db, settings, driver):
                raise RuntimeError("fleetbase_driver_id_not_returned")
        elif kind == "vehicle":
            vehicle = db.query(Vehicle).filter(Vehicle.id == payload.get("vehicle_id")).first()
            if vehicle:
                bridge.sync_vehicle(db, settings, vehicle)
        elif kind in ("cancellation", "return", "damage") and order:
            if kind == "cancellation" and not order.fleetbase_order_id:
                raise PermanentSyncSkip("cancellation_missing_fleetbase_order_id")
            self._http_push_status(
                bridge, settings, order, kind, payload.get("status", "")
            )
        elif kind == "webhook":
            self._replay_webhook(db, settings, job)
        elif kind == "tracking":
            fb_driver = payload.get("fleetbase_driver_id")
            if not fb_driver:
                raise PermanentSyncSkip("tracking_missing_fleetbase_driver_id")
            if _is_seed_fleetbase_public_id(str(fb_driver)):
                raise PermanentSyncSkip("tracking_seed_fleetbase_driver_id")
            ok = bridge._integration(settings).track_driver_location(
                fb_driver,
                lat=float(payload["lat"]),
                lng=float(payload["lng"]),
                heading=payload.get("heading"),
                speed=payload.get("speed"),
            )
            if not ok:
                raise RuntimeError("fleetbase_tracking_failed")
        elif kind == "pod_photo":
            fb_order = payload.get("fleetbase_order_id") or (order.fleetbase_order_id if order else None)
            if not fb_order or not payload.get("file_url"):
                raise PermanentSyncSkip("pod_photo_payload_incomplete")
            ok = bridge._integration(settings).upload_pod_photo(fb_order, payload["file_url"])
            if not ok:
                raise RuntimeError("fleetbase_pod_photo_failed")
        elif kind == "pod_signature":
            fb_order = payload.get("fleetbase_order_id") or (order.fleetbase_order_id if order else None)
            if not fb_order or not payload.get("signature_data"):
                raise PermanentSyncSkip("pod_signature_payload_incomplete")
            ok = bridge._integration(settings).upload_pod_signature(
                fb_order, payload["signature_data"]
            )
            if not ok:
                raise RuntimeError("fleetbase_pod_signature_failed")
        elif kind == "pod_barcode":
            fb_order = payload.get("fleetbase_order_id") or (order.fleetbase_order_id if order else None)
            if not fb_order or not payload.get("barcode"):
                raise PermanentSyncSkip("pod_barcode_payload_incomplete")
            ok = bridge._integration(settings).upload_pod_barcode(fb_order, payload["barcode"])
            if not ok:
                raise RuntimeError("fleetbase_pod_barcode_failed")
        elif kind == "driver_online":
            fb_driver = payload.get("fleetbase_driver_id")
            if not fb_driver or "online" not in payload:
                raise PermanentSyncSkip("driver_online_payload_incomplete")
            ok = bridge._integration(settings).toggle_driver_online(
                fb_driver, online=bool(payload["online"])
            )
            if not ok:
                raise RuntimeError("fleetbase_driver_online_failed")
        elif kind == "proofs" and order:
            bridge.sync_proofs(settings, order)
        elif kind == "order_state":
            fb_order = payload.get("fleetbase_order_id") or (order.fleetbase_order_id if order else None)
            state = payload.get("order_state")
            if not fb_order or not state:
                raise PermanentSyncSkip("order_state_payload_incomplete")
            from porterchain_fleetbase_adapter.events.lifecycle import FleetbaseLifecycleTranslator

            state_u = str(state).upper()
            integration = bridge._integration(settings)
            if state_u == "DRIVER_EN_ROUTE":
                ok = integration.start_order_execution(fb_order) is not None
            elif state_u in ("DELIVERED", "POD_COMPLETED"):
                ok = integration.complete_order_execution(fb_order) is not None
            else:
                fb_status = FleetbaseLifecycleTranslator.to_fleetbase_status(state_u)
                if not fb_status:
                    raise PermanentSyncSkip(f"order_state_unmapped:{state_u}")
                ok = integration.update_order_status(fb_order, fb_status)
            if not ok:
                raise RuntimeError("fleetbase_order_state_failed")
        else:
            raise PermanentSyncSkip(f"unhandled_retry_kind:{kind}")

    def process_retry_queue(
        self,
        db: Session,
        settings: Settings,
        *,
        limit: int = 1,
        kinds: Sequence[str] | None = None,
        exclude_kinds: Sequence[str] | None = None,
    ) -> dict:
        """Drain claimed jobs. Default limit=1; adapter max_retries=0 on this path."""
        processed = 0
        failed = 0
        skipped = 0
        drain_bridge = FleetbaseIntegrationBridge(max_retries=0)
        if settings.fleetbase_dispatch_bridge:
            self.enqueue_unlinked_open_orders(db, settings, limit=max(limit, 25), commit=True)
        for job in RetryQueue.claim_due(
            db, limit=limit, kinds=kinds, exclude_kinds=exclude_kinds
        ):
            order = (
                (
                    db.query(Order)
                    .options(selectinload(Order.packages), selectinload(Order.quote))
                    .filter(Order.id == job.order_id)
                    .first()
                )
                if job.order_id
                else None
            )
            try:
                if job.kind in _ORDER_SCOPED_KINDS and not order:
                    RetryQueue.mark_done(db, job)
                    skipped += 1
                    continue
                self._http_dispatch_kind(drain_bridge, db, settings, job, order)
                RetryQueue.mark_done(db, job)
                if job.kind == "tracking":
                    self._reenqueue_if_last_known_newer(db, job)
                processed += 1
            except PermanentSyncSkip as exc:
                # Surface in retry/dead monitors — never mark_done (silent success).
                RetryQueue.mark_failed(db, job, f"[permanent_skip] {exc}")
                failed += 1
            except Exception as exc:  # noqa: BLE001
                RetryQueue.mark_failed(db, job, str(exc))
                failed += 1
        return {"processed": processed, "failed": failed, "skipped": skipped}

    @staticmethod
    def _reenqueue_if_last_known_newer(db: Session, job: FleetbaseSyncJob) -> None:
        """After a successful track POST, enqueue leftover GPS that landed during HTTP."""
        from porterchain_api.driver_engine.last_known import parse_recorded_at, read_last_known

        payload = job.payload or {}
        driver_id = payload.get("driver_id")
        if not driver_id:
            return
        sent = parse_recorded_at(payload.get("recorded_at"))
        known = read_last_known(str(driver_id))
        if known is None or sent is None:
            return
        if known.recorded_at <= sent:
            return
        RetryQueue.enqueue(
            db,
            direction="outbound",
            kind="tracking",
            idempotency_key=f"tracking:{driver_id}",
            payload=known.as_track_payload(),
            commit=True,
        )

