"""Domain event → Notification Engine routing. Recipients resolved here only."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_api.db import SessionLocal
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

_notification_handlers_registered = False

PRIORITY_MAP = {
    DomainEventType.PAYMENT_FAILED: "critical",
    DomainEventType.DRIVER_ASSIGNED: "high",
    DomainEventType.ORDER_NEAR_DELIVERY: "high",
}


def _ctx(payload: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in payload.items() if v is not None}


def _tags(payload: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "order_id",
        "order_number",
        "tracking_number",
        "booking_number",
        "merchant_id",
        "customer_id",
        "driver_id",
        "claim_id",
        "ticket_id",
        "invoice_number",
    )
    return {k: payload[k] for k in keys if payload.get(k)}


def _specs_for_event(event_type: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    ctx = _ctx(payload)
    tags = _tags(payload)
    priority = PRIORITY_MAP.get(event_type, "normal")  # type: ignore[arg-type]
    specs: list[dict[str, Any]] = []

    def add(
        template: str,
        channel: str,
        recipient_type: str,
        recipient_id: str,
        *,
        address: str | None = None,
        category: str | None = None,
    ) -> None:
        if not recipient_id:
            return
        specs.append(
            {
                "template_key": template,
                "channel": channel,
                "recipient_type": recipient_type,
                "recipient_id": recipient_id,
                "recipient_address": address,
                "context": ctx,
                "search_tags": tags,
                "category": category,
                "priority": priority,
            }
        )

    email = payload.get("email") or payload.get("contact_email")
    customer_id = payload.get("customer_id")
    merchant_id = payload.get("merchant_id")
    driver_id = payload.get("driver_id") or payload.get("assigned_driver_id")

    if event_type == DomainEventType.BOOKING_DRAFT_CREATED:
        if customer_id:
            add("booking_draft_created", "in_app", "customer", customer_id)
        if email and customer_id:
            add("booking_draft_created", "email", "customer", customer_id, address=email)

    elif event_type == DomainEventType.BOOKING_CONFIRMED:
        if customer_id:
            add("booking_confirmed", "in_app", "customer", customer_id)
            add("booking_confirmed", "push", "customer", customer_id)
        if email and customer_id:
            add("booking_confirmed", "email", "customer", customer_id, address=email)
        if merchant_id:
            add("booking_confirmed", "in_app", "merchant", merchant_id)
        add("booking_confirmed", "in_app", "admin", "system")

    elif event_type in (DomainEventType.PAYMENT_STARTED, DomainEventType.CHECKOUT_STARTED):
        if customer_id:
            add("payment_started", "in_app", "customer", customer_id)

    elif event_type == DomainEventType.PAYMENT_SUCCEEDED:
        if customer_id:
            add("payment_receipt", "in_app", "customer", customer_id)
        if email and customer_id:
            add("payment_receipt", "email", "customer", customer_id, address=email)
        if merchant_id:
            add("payment_receipt", "in_app", "merchant", merchant_id)
        add("payment_receipt", "in_app", "finance", "system")

    elif event_type == DomainEventType.PAYMENT_FAILED:
        if customer_id:
            add("payment_failed", "in_app", "customer", customer_id)
        if email and customer_id:
            add("payment_failed", "email", "customer", customer_id, address=email)

    elif event_type in (DomainEventType.ORDER_CREATED, DomainEventType.ORDER_BOOKED):
        template = "order_created" if event_type == DomainEventType.ORDER_CREATED else "order_booked"
        if customer_id:
            add(template, "in_app", "customer", customer_id)
        if email and customer_id:
            add(template, "email", "customer", customer_id, address=email)
        if merchant_id:
            add(template, "in_app", "merchant", merchant_id)
        add(template, "in_app", "admin", "system")

    elif event_type == DomainEventType.DRIVER_ASSIGNED:
        if customer_id:
            add("driver_assigned", "in_app", "customer", customer_id)
            add("driver_assigned", "push", "customer", customer_id)
        if driver_id:
            add("driver_assigned", "push", "driver", driver_id, category="tracking")
            add("driver_assigned", "in_app", "driver", driver_id, category="tracking")
        if merchant_id:
            add("driver_assigned", "in_app", "merchant", merchant_id)
        add("driver_assigned", "in_app", "admin", "system")

    elif event_type == DomainEventType.DRIVER_ACCEPTED:
        if driver_id:
            add("driver_accepted", "in_app", "driver", driver_id)
        add("driver_accepted", "in_app", "admin", "system")

    elif event_type == DomainEventType.DRIVER_REJECTED:
        add("driver_rejected", "in_app", "admin", "system")

    elif event_type == DomainEventType.DRIVER_ARRIVED_PICKUP:
        if customer_id:
            add("pickup_started", "push", "customer", customer_id)
        add("pickup_started", "in_app", "admin", "system")

    elif event_type == DomainEventType.PARCEL_PICKED_UP:
        if customer_id:
            add("parcel_picked_up", "push", "customer", customer_id)
        add("parcel_picked_up", "in_app", "admin", "system")

    elif event_type == DomainEventType.DELIVERY_STARTED:
        if customer_id:
            add("in_transit", "push", "customer", customer_id)

    elif event_type == DomainEventType.ORDER_NEAR_DELIVERY:
        if customer_id:
            add("near_delivery", "push", "customer", customer_id)

    elif event_type == DomainEventType.PARCEL_DELIVERED:
        if customer_id:
            add("delivered", "in_app", "customer", customer_id)
            add("delivered", "push", "customer", customer_id)
        if driver_id:
            add("delivered", "in_app", "driver", driver_id)
        add("delivered", "in_app", "admin", "system")

    elif event_type == DomainEventType.PROOF_COMPLETED:
        add("pod_uploaded", "in_app", "admin", "system")
        if driver_id:
            add("pod_uploaded", "in_app", "driver", driver_id)

    elif event_type == DomainEventType.INVOICE_GENERATED:
        if customer_id:
            add("invoice_ready", "email", "customer", customer_id, address=email)
        if merchant_id:
            add("merchant_invoice_ready", "in_app", "merchant", merchant_id)
        add("invoice_ready", "in_app", "finance", "system")

    elif event_type == DomainEventType.MERCHANT_BILLED:
        if merchant_id:
            add("merchant_invoice_ready", "in_app", "merchant", merchant_id)
        add("merchant_invoice_ready", "in_app", "finance", "system")

    elif event_type == DomainEventType.REFUND_ISSUED:
        if customer_id:
            add("refund_processed", "in_app", "customer", customer_id)
        if email and customer_id:
            add("refund_processed", "email", "customer", customer_id, address=email)

    elif event_type == DomainEventType.CLAIM_OPENED:
        if customer_id:
            add("claim_opened", "in_app", "customer", customer_id)
        if email and customer_id:
            add("claim_opened", "email", "customer", customer_id, address=email)
        reporter = payload.get("actor_id") or payload.get("driver_id")
        if reporter and payload.get("actor_type") == "driver":
            add("claim_opened", "push", "driver", reporter, category="claims")
            add("claim_opened", "in_app", "driver", reporter, category="claims")
        add("claim_opened", "in_app", "support", "system")

    elif event_type == DomainEventType.CLAIM_RESOLVED:
        if customer_id:
            add("claim_updated", "in_app", "customer", customer_id)
        reporter = payload.get("driver_id")
        if reporter:
            add("claim_updated", "push", "driver", reporter, category="claims")
            add("claim_updated", "in_app", "driver", reporter, category="claims")
        add("claim_updated", "in_app", "support", "system")

    elif event_type == DomainEventType.SUPPORT_TICKET_CREATED:
        if customer_id:
            add("support_ticket_created", "in_app", "customer", customer_id)
        if email and customer_id:
            add("support_ticket_created", "email", "customer", customer_id, address=email)
        ticket_driver = payload.get("driver_id")
        if ticket_driver:
            add("support_ticket_created", "push", "driver", ticket_driver, category="support")
            add("support_ticket_created", "in_app", "driver", ticket_driver, category="support")
        add("support_ticket_created", "in_app", "support", "system")

    elif event_type in (DomainEventType.ORDER_TEMP_EXCURSION, "order.temp_excursion"):
        add("temp_excursion", "email", "admin", "system", category="orders")
        specs[-1]["priority"] = "high"
        if merchant_id:
            add("temp_excursion", "in_app", "merchant", merchant_id, category="orders")
            specs[-1]["priority"] = "high"

    elif event_type == "driver.emergency":
        add("driver_alert", "in_app", "admin", "system", category="security")
        specs[-1]["priority"] = "critical"

    elif event_type == "driver.route_changed":
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_route_changed", "push", "driver", did, category="tracking")
            add("driver_route_changed", "in_app", "driver", did, category="tracking")

    elif event_type == "incident.reported":
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_alert", "in_app", "driver", did, category="support")
        add("driver_alert", "in_app", "admin", "system", category="support")

    elif event_type in ("driver.shift_started", "driver.shift_ended", "driver.break_started", "driver.break_resumed"):
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_alert", "in_app", "driver", did, category="orders")

    elif event_type == DomainEventType.FLEETBASE_STATUS_UPDATED:
        ctx.setdefault("message", payload.get("status", "Status updated"))
        if customer_id:
            add("tracking_update", "push", "customer", customer_id)
            add("tracking_update", "in_app", "customer", customer_id)

    return specs


def handle_domain_event(envelope: dict[str, Any]) -> None:
    event_type = envelope.get("event_type", "")
    payload = envelope.get("payload") or {}
    specs = _specs_for_event(event_type, payload)
    if not specs:
        return

    db = SessionLocal()
    try:
        engine = get_notification_engine()
        engine.dispatch_multi(
            db,
            specs,
            event_type=event_type,
            correlation_id=envelope.get("correlation_id") or envelope.get("aggregate_id"),
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("notification event routing failed: %s", exc)
        db.rollback()
    finally:
        db.close()


def register_notification_handlers() -> None:
    from porterchain_event_bus.registry import get_handler_registry

    global _notification_handlers_registered
    if _notification_handlers_registered:
        return
    _notification_handlers_registered = True

    registry = get_handler_registry()
    watched = [
        DomainEventType.BOOKING_DRAFT_CREATED,
        DomainEventType.BOOKING_CONFIRMED,
        DomainEventType.CHECKOUT_STARTED,
        DomainEventType.PAYMENT_STARTED,
        DomainEventType.PAYMENT_SUCCEEDED,
        DomainEventType.PAYMENT_FAILED,
        DomainEventType.ORDER_CREATED,
        DomainEventType.ORDER_BOOKED,
        DomainEventType.DRIVER_ASSIGNED,
        DomainEventType.DRIVER_ACCEPTED,
        DomainEventType.DRIVER_REJECTED,
        DomainEventType.DRIVER_ARRIVED_PICKUP,
        DomainEventType.PARCEL_PICKED_UP,
        DomainEventType.DELIVERY_STARTED,
        DomainEventType.ORDER_NEAR_DELIVERY,
        DomainEventType.PARCEL_DELIVERED,
        DomainEventType.PROOF_COMPLETED,
        DomainEventType.INVOICE_GENERATED,
        DomainEventType.MERCHANT_BILLED,
        DomainEventType.REFUND_ISSUED,
        DomainEventType.CLAIM_OPENED,
        DomainEventType.CLAIM_RESOLVED,
        DomainEventType.SUPPORT_TICKET_CREATED,
        DomainEventType.FLEETBASE_STATUS_UPDATED,
        DomainEventType.ORDER_TEMP_EXCURSION,
    ]
    for evt in watched:
        registry.subscribe(evt, handle_domain_event)
    for evt in ("driver.emergency", "driver.route_changed"):
        registry.subscribe(evt, handle_domain_event)
    for evt in (
        "incident.reported",
        "driver.shift_started",
        "driver.shift_ended",
        "driver.break_started",
        "driver.break_resumed",
    ):
        registry.subscribe(evt, handle_domain_event)
