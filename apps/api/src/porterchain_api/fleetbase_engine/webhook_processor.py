"""WebhookProcessor — inbound Fleetbase → Porterchain status/tracking sync.

Branches a Fleetbase webhook update by kind (status, tracking, POD, driver
assignment, exception, claim), reconciles it onto the canonical Porterchain
order, raises the matching exceptions/claims, and emits domain events that drive
merchant/customer dashboards + notifications. Failures are retried (inbound queue).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from porterchain_api.admin_models import Claim, Driver
from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.fleetbase_sync_service import FleetbaseSyncService
from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.audit_logger import AuditLogger
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.fleetbase_engine.status_translator import StatusTranslator
from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_api.models import Order, OrderException

logger = logging.getLogger(__name__)


class WebhookProcessor:
    def __init__(self) -> None:
        self._sync = FleetbaseSyncService()

    def _resolve_order(self, db: Session, update: dict) -> Order | None:
        pc = update.get("porterchain_order_id")
        fb = update.get("fleetbase_order_id")
        order = None
        if pc:
            order = db.query(Order).filter(Order.id == pc).first()
        if not order and fb:
            order = db.query(Order).filter(Order.fleetbase_order_id == fb).first()
        return order

    def process(self, db: Session, settings: Settings, update: dict, raw: dict | None = None) -> Order | None:
        event = update.get("event")
        kind = StatusTranslator.classify(event)
        order = self._resolve_order(db, update)

        if not order:
            AuditLogger.log(
                db, direction="inbound", kind=kind, status="skipped",
                fleetbase_order_id=update.get("fleetbase_order_id"),
                message="order_not_found", detail={"event": event},
            )
            return None

        try:
            # Ensure a target_state is present for state-changing events.
            if kind in ("status", "pod", "exception", "driver") and not update.get("target_state"):
                mapped = StatusTranslator.to_state(event=event, status=update.get("status"))
                if mapped:
                    update["target_state"] = mapped.value

            if kind == "tracking":
                self._handle_tracking(db, order, raw or update)
            else:
                # Base status + POD handling (canonical transition).
                self._sync.apply_webhook_update(db, settings, update)
                if kind == "exception":
                    self._raise_exception(db, order, event)
                elif kind == "claim":
                    self._open_claim(db, order, event)
                elif kind == "driver":
                    self._map_driver(db, order, update)

            # Fan out a Porterchain domain event for dashboards + notifications.
            emit_event(
                db,
                event_type=f"order.{kind}_synced",
                aggregate_type="order",
                aggregate_id=order.id,
                actor_type="fleetbase",
                payload={"event": event, "state": order.state},
            )
            AuditLogger.log(
                db, direction="inbound", kind=kind, status="ok",
                order_id=order.id, fleetbase_order_id=order.fleetbase_order_id,
                message=event, detail={"state": order.state},
            )
            return order
        except Exception as exc:  # noqa: BLE001 — durable retry
            logger.exception("Fleetbase webhook processing failed for %s", order.id)
            db.rollback()
            RetryQueue.enqueue(
                db, direction="inbound", kind="webhook", order_id=order.id,
                fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"webhook:{order.id}:{event}",
                payload={"update": update},
            )
            AuditLogger.log(db, direction="inbound", kind=kind, status="error",
                            order_id=order.id, message=str(exc), detail={"event": event})
            return None

    # ------------------------------------------------------------------ #
    def _handle_tracking(self, db: Session, order: Order, raw: dict[str, Any]) -> None:
        snapshot = TrackingTranslator.translate(raw)
        emit_event(
            db,
            event_type="order.tracking_updated",
            aggregate_type="order",
            aggregate_id=order.id,
            actor_type="fleetbase",
            payload={"tracking": snapshot},
        )
        db.commit()

    def _raise_exception(self, db: Session, order: Order, event: str | None) -> None:
        ex_type = StatusTranslator.exception_type(event)
        existing = (
            db.query(OrderException)
            .filter(OrderException.order_id == order.id, OrderException.type == ex_type, OrderException.status == "open")
            .first()
        )
        if existing:
            return
        db.add(
            OrderException(
                order_id=order.id,
                type=ex_type,
                status="open",
                reported_by_type="fleetbase",
                evidence={"event": event},
            )
        )
        db.commit()

    def _open_claim(self, db: Session, order: Order, event: str | None) -> None:
        existing = db.query(Claim).filter(Claim.order_id == order.id, Claim.status == "open").first()
        if existing:
            return
        claim_type = "damage" if "damage" in (event or "") else "loss" if "lost" in (event or "") else "general"
        db.add(Claim(order_id=order.id, claim_type=claim_type, status="open", description=f"Opened from Fleetbase event {event}"))
        db.commit()

    def _map_driver(self, db: Session, order: Order, update: dict) -> None:
        fb_driver = update.get("fleetbase_driver_id") or (update.get("driver") or {}).get("id")
        if not fb_driver:
            return
        driver = db.query(Driver).filter(Driver.fleetbase_driver_id == fb_driver).first()
        if driver and order.assigned_driver_id != driver.id:
            order.assigned_driver_id = driver.id
            db.commit()
