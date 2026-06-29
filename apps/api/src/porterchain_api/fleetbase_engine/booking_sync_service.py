"""BookingSyncService — outbound Porterchain → Fleetbase order synchronisation.

Reacts to domain events (never called by the frontend). Pushes order creation,
driver assignment, cancellation, return, damage and claim state to Fleetbase via
the adapter, with durable retry + audit. The order state machine stays canonical
in Porterchain; Fleetbase mirrors execution.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.fleetbase_sync_service import FleetbaseSyncService
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.audit_logger import AuditLogger
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.models import Order
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration

logger = logging.getLogger(__name__)


class BookingSyncService:
    def __init__(self) -> None:
        self._sync = FleetbaseSyncService()

    # ------------------------------------------------------------------ #
    # Order create / update
    # ------------------------------------------------------------------ #
    def push_order(self, db: Session, settings: Settings, order: Order) -> str | None:
        """Create/update the Fleetbase order; retry + audit on failure."""
        if not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(db, direction="outbound", kind="order", status="skipped",
                            order_id=order.id, message="dispatch_bridge_disabled")
            return None
        try:
            fleetbase_id = self._sync.sync_order(db, settings, order)
            AuditLogger.log(
                db, direction="outbound", kind="order", status="ok",
                order_id=order.id, fleetbase_order_id=fleetbase_id,
                message="order synced to Fleetbase",
            )
            return fleetbase_id
        except Exception as exc:  # noqa: BLE001 — durable retry
            logger.exception("Fleetbase order sync failed for %s", order.id)
            RetryQueue.enqueue(
                db, direction="outbound", kind="order",
                order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"order:{order.id}",
                payload={"order_id": order.id},
            )
            AuditLogger.log(db, direction="outbound", kind="order", status="error",
                            order_id=order.id, message=str(exc))
            return None

    # ------------------------------------------------------------------ #
    # Driver assignment
    # ------------------------------------------------------------------ #
    def push_driver_assignment(
        self, db: Session, settings: Settings, order: Order, *, fleetbase_driver_id: str | None
    ) -> None:
        if not order.fleetbase_order_id:
            self.push_order(db, settings, order)
        try:
            self._sync.sync_dispatch(settings, order, fleetbase_driver_id=fleetbase_driver_id)
            AuditLogger.log(db, direction="outbound", kind="driver", status="ok",
                            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
                            detail={"fleetbase_driver_id": fleetbase_driver_id})
        except Exception as exc:  # noqa: BLE001
            RetryQueue.enqueue(
                db, direction="outbound", kind="driver", order_id=order.id,
                fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"driver:{order.id}:{fleetbase_driver_id}",
                payload={"order_id": order.id, "fleetbase_driver_id": fleetbase_driver_id},
            )
            AuditLogger.log(db, direction="outbound", kind="driver", status="error",
                            order_id=order.id, message=str(exc))

    # ------------------------------------------------------------------ #
    # Exception sync (cancellation / return / damage / claim)
    # ------------------------------------------------------------------ #
    def _push_status(self, db: Session, settings: Settings, order: Order, kind: str, status: str) -> None:
        """Best-effort push of an exception status to Fleetbase, with retry."""
        if not order.fleetbase_order_id or not settings.fleetbase_dispatch_bridge:
            AuditLogger.log(db, direction="outbound", kind=kind, status="skipped",
                            order_id=order.id, message="no_fleetbase_id_or_bridge_disabled")
            return
        integration = get_fleetbase_integration(settings)
        try:
            # Adapter exposes order updates via sync_order; reuse with status hint.
            updater = getattr(integration, "update_order_status", None)
            if callable(updater):
                updater(order.fleetbase_order_id, status)
            else:
                integration.sync_order(
                    {
                        "fleetbase_order_id": order.fleetbase_order_id,
                        "porterchain_order_id": order.id,
                        "status": status,
                    }
                )
            AuditLogger.log(db, direction="outbound", kind=kind, status="ok",
                            order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
                            detail={"status": status})
        except Exception as exc:  # noqa: BLE001
            RetryQueue.enqueue(
                db, direction="outbound", kind=kind, order_id=order.id,
                fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"{kind}:{order.id}",
                payload={"order_id": order.id, "status": status},
            )
            AuditLogger.log(db, direction="outbound", kind=kind, status="error",
                            order_id=order.id, message=str(exc))

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
    def process_retry_queue(self, db: Session, settings: Settings, *, limit: int = 50) -> dict:
        processed = 0
        failed = 0
        for job in RetryQueue.due(db, limit=limit):
            order = db.query(Order).filter(Order.id == job.order_id).first() if job.order_id else None
            try:
                if job.kind == "order" and order:
                    self._sync.sync_order(db, settings, order)
                elif job.kind == "driver" and order:
                    self._sync.sync_dispatch(
                        settings, order, fleetbase_driver_id=job.payload.get("fleetbase_driver_id")
                    )
                elif job.kind in ("cancellation", "return", "damage") and order:
                    self._push_status(db, settings, order, job.kind, job.payload.get("status", ""))
                RetryQueue.mark_done(db, job)
                processed += 1
            except Exception as exc:  # noqa: BLE001
                RetryQueue.mark_failed(db, job, str(exc))
                failed += 1
        return {"processed": processed, "failed": failed}
