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

from porterchain_api.booking_engine._core import emit_event
from porterchain_api.booking_engine.order_transitions import transition_order_state
from porterchain_api.config import Settings
from porterchain_api.domain.states import OrderState
from porterchain_api.fleetbase_engine.audit_logger import AuditLogger
from porterchain_api.fleetbase_engine.integration_bridge import FleetbaseIntegrationBridge
from porterchain_api.fleetbase_engine.retry_queue import RetryQueue
from porterchain_api.fleetbase_engine.status_translator import StatusTranslator
from porterchain_api.fleetbase_engine.tracking_facade import TrackingFacade
from porterchain_api.booking_models import Order, OrderException
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)


class WebhookProcessor:
    def __init__(self) -> None:
        self._bridge = FleetbaseIntegrationBridge()

    def apply_status_update(self, db: Session, settings: Settings, update: dict) -> Order | None:
        """Apply Fleetbase status/POD webhook to the canonical Porterchain order."""
        order_id = update.get("porterchain_order_id")
        fleetbase_id = update.get("fleetbase_order_id")
        order: Order | None = None

        if order_id:
            order = db.query(Order).filter(Order.id == order_id).first()
        if not order and fleetbase_id:
            order = db.query(Order).filter(Order.fleetbase_order_id == fleetbase_id).first()
        if not order:
            logger.warning("Fleetbase webhook: order not found pc=%s fb=%s", order_id, fleetbase_id)
            return None

        target_state = update.get("target_state")
        if target_state:
            try:
                new_state = OrderState(target_state)
                current = OrderState(order.state)
                if new_state != current:
                    transition_order_state(
                        db,
                        order,
                        new_state,
                        event_type=update.get("domain_event") or f"fleetbase.{update.get('event')}",
                        actor_type="fleetbase",
                        payload={"fleetbase_event": update.get("event")},
                    )
                    emit_event(
                        db,
                        event_type=DomainEventType.FLEETBASE_STATUS_UPDATED,
                        aggregate_type="order",
                        aggregate_id=order.id,
                        actor_type="fleetbase",
                        payload={
                            "fleetbase_event": update.get("event"),
                            "from_state": current.value,
                            "to_state": new_state.value,
                            "status": new_state.value,
                            "fleetbase_order_id": order.fleetbase_order_id,
                            "order_id": order.id,
                            "order_number": order.order_number,
                            "tracking_number": order.tracking_number,
                            "customer_id": order.customer_id,
                            "merchant_id": order.merchant_id,
                            "driver_id": order.assigned_driver_id,
                        },
                    )
            except ValueError as exc:
                logger.warning("Invalid state transition from webhook: %s", exc)

        if update.get("event") == "order.completed":
            # Apply PC POD state; Fleetbase proof pull runs in drain (no inline HTTP).
            RetryQueue.enqueue(
                db,
                direction="outbound",
                kind="proofs",
                order_id=order.id,
                fleetbase_order_id=order.fleetbase_order_id,
                idempotency_key=f"proofs:{order.id}",
                payload={"order_id": order.id},
                commit=False,
            )
            if order.state == OrderState.DELIVERED.value:
                proof_count = update.get("proof_count")
                transition_order_state(
                    db,
                    order,
                    OrderState.POD_COMPLETED,
                    event_type="order.pod_completed",
                    actor_type="fleetbase",
                    payload={"proof_count": int(proof_count) if proof_count is not None else 0},
                )
                emit_event(
                    db,
                    event_type=DomainEventType.FLEETBASE_POD_RECEIVED,
                    aggregate_type="order",
                    aggregate_id=order.id,
                    actor_type="fleetbase",
                    payload={
                        "proof_count": int(proof_count) if proof_count is not None else 0,
                        "fleetbase_order_id": order.fleetbase_order_id,
                    },
                )

        db.refresh(order)
        return order

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

        # D-26: driver presence does not require an order — mirror onto Driver.is_online.
        if kind == "presence":
            try:
                driver = self._mirror_driver_presence(db, update)
                AuditLogger.log(
                    db,
                    direction="inbound",
                    kind=kind,
                    status="ok" if driver else "skipped",
                    message=event,
                    detail={
                        "fleetbase_driver_id": update.get("fleetbase_driver_id"),
                        "online": update.get("online"),
                        "driver_id": getattr(driver, "id", None),
                    },
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("Fleetbase presence webhook failed: %s", exc)
                AuditLogger.log(
                    db,
                    direction="inbound",
                    kind=kind,
                    status="error",
                    message=str(exc),
                    detail={"event": event},
                )
            return None

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
                self.apply_status_update(db, settings, update)
                if kind == "exception":
                    self._raise_exception(db, order, event)
                elif kind == "claim":
                    self._open_claim(db, order, event)
                elif kind == "driver":
                    self._map_driver(db, order, update)

            # Opportunistic presence mirror when the payload carries online.
            if update.get("online") is not None:
                self._mirror_driver_presence(db, update)

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
        snapshot = TrackingFacade.translate_live(raw)
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
        exc = OrderException(
            order_id=order.id,
            type=ex_type,
            status="open",
            reported_by_type="fleetbase",
            evidence={"event": event},
        )
        db.add(exc)
        db.flush()
        emit_event(
            db,
            event_type=DomainEventType.EXCEPTION_OPENED,
            aggregate_type="order",
            aggregate_id=order.id,
            actor_type="fleetbase",
            payload={
                "exception_id": exc.id,
                "exception_type": ex_type,
                "order_id": order.id,
                "order_number": order.order_number,
                "tracking_number": order.tracking_number,
                "customer_id": order.customer_id,
                "merchant_id": order.merchant_id,
                "driver_id": order.assigned_driver_id,
                "message": f"Exception opened: {ex_type}",
            },
        )
        db.commit()

    def _open_claim(self, db: Session, order: Order, event: str | None) -> None:
        from porterchain_api.support_engine.claims_service import AdminClaimsService

        claim_type = "damage" if "damage" in (event or "") else "loss" if "lost" in (event or "") else "general"
        AdminClaimsService().open_actor_claim(
            db,
            order_id=order.id,
            claim_type=claim_type,
            description=f"Opened from Fleetbase event {event}",
            status="open",
            actor_type="fleetbase",
            skip_if_open=True,
        )

    def _map_driver(self, db: Session, order: Order, update: dict) -> None:
        from porterchain_api.admin_engine.driver_lookups import get_driver_by_fleetbase_id

        fb_driver = update.get("fleetbase_driver_id") or (update.get("driver") or {}).get("id")
        if not fb_driver:
            resource = update.get("resource") if isinstance(update.get("resource"), dict) else {}
            nested = resource.get("driver") if isinstance(resource.get("driver"), dict) else {}
            fb_driver = nested.get("id") or nested.get("uuid")
        if not fb_driver:
            return
        driver = get_driver_by_fleetbase_id(db, fb_driver)
        if driver and order.assigned_driver_id != driver.id:
            order.assigned_driver_id = driver.id
            db.commit()

    def _mirror_driver_presence(self, db: Session, update: dict) -> Any | None:
        """Mirror Fleetbase online/availability onto the local Driver row (D-26)."""
        resource = update.get("resource") if isinstance(update.get("resource"), dict) else {}
        fb_driver = update.get("fleetbase_driver_id")
        if not fb_driver:
            nested = resource.get("driver") if isinstance(resource.get("driver"), dict) else {}
            fb_driver = (
                nested.get("uuid")
                or nested.get("id")
                or resource.get("uuid")
                or resource.get("id")
                or (update.get("driver") or {}).get("id")
            )
        if not fb_driver:
            return None

        online = update.get("online")
        if online is None:
            body = resource.get("driver") if isinstance(resource.get("driver"), dict) else resource
            if isinstance(body, dict):
                if isinstance(body.get("online"), bool):
                    online = body["online"]
                else:
                    status = str(body.get("status") or "").lower()
                    if status in {"online", "active"}:
                        online = True
                    elif status in {"offline", "inactive"}:
                        online = False
        if online is None:
            event = str(update.get("event") or "").lower()
            if event in {"driver.online", "driver.toggled_online"}:
                online = True
            elif event == "driver.offline":
                online = False
        if online is None:
            return None

        from porterchain_api.admin_engine.driver_lookups import (
            get_driver_by_fleetbase_id,
            persist_presence,
        )

        driver = get_driver_by_fleetbase_id(db, str(fb_driver))
        if not driver:
            return None
        persist_presence(db, driver, is_online=bool(online))
        return driver
