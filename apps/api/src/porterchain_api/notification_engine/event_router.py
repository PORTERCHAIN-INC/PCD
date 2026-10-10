"""Domain event → Notification Engine routing. Recipients resolved here only."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_api.db import SessionLocal
from porterchain_api.notification_engine.context import (
    deep_link_for,
    hydrate_order_context,
    merge_notification_context,
)
from porterchain_api.notification_engine.engine import get_notification_engine
from porterchain_api.notification_engine.preference_service import drop_muted_merchant_specs
from porterchain_api.notification_engine.route_table import specs_for_parcel
from porterchain_api.notification_engine.staff_fanout import expand_staff_specs, staff_sentinel
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

_notification_handlers_registered = False

PRIORITY_MAP = {
    DomainEventType.PAYMENT_FAILED: "critical",
    DomainEventType.DRIVER_ASSIGNED: "high",
    DomainEventType.ORDER_NEAR_DELIVERY: "high",
    DomainEventType.EXCEPTION_OPENED: "high",
    DomainEventType.ORDER_DELAYED: "high",
    DomainEventType.SLA_BREACHED: "critical",
    DomainEventType.EXCEPTION_RESOLVED: "normal",
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
        "exception_id",
        "exception_type",
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
        pri: str | None = None,
        dedupe: str | None = None,
        dedupe_window: int | None = None,
    ) -> None:
        if not recipient_id:
            return
        extra: dict[str, Any] = {}
        if dedupe:
            extra["dedupe_family"] = dedupe
            extra["dedupe_window_sec"] = dedupe_window
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
                "priority": pri or priority,
                "deep_link": deep_link_for(recipient_type, payload),
                **extra,
            }
        )

    def add_staff(template: str, channel: str, topic: str, *, category: str | None = None, pri: str | None = None) -> None:
        add(template, channel, "admin", staff_sentinel(topic), category=category, pri=pri)  # type: ignore[arg-type]

    # One routing table: parcel/delivery moments are owned by route_table; the
    # branches below cover only events route_table does not claim.
    if specs_for_parcel(event_type, payload, add):
        return specs

    email = payload.get("email") or payload.get("contact_email")
    customer_id = payload.get("customer_id")
    merchant_id = payload.get("merchant_id")
    driver_id = payload.get("driver_id") or payload.get("assigned_driver_id")

    if event_type == DomainEventType.NEWSLETTER_CONFIRM_REQUESTED:
        # Double opt-in confirmation — transactional (crm), one email to the subscriber only.
        subscriber_id = payload.get("subscriber_id")
        if subscriber_id and email:
            add(
                "newsletter_confirm",
                "email",
                "subscriber",
                subscriber_id,
                address=email,
                category="crm",
            )
        return specs

    if event_type == DomainEventType.BOOKING_DRAFT_CREATED:
        if customer_id:
            add("booking_draft_created", "in_app", "customer", customer_id)
        if email and customer_id:
            add("booking_draft_created", "email", "customer", customer_id, address=email)

    elif event_type in (DomainEventType.PAYMENT_STARTED, DomainEventType.CHECKOUT_STARTED):
        if customer_id:
            add("payment_started", "in_app", "customer", customer_id)

    elif event_type in (DomainEventType.PAYMENT_SUCCEEDED, "receipt.generated"):
        if customer_id:
            add("payment_receipt", "in_app", "customer", customer_id)
        if email and customer_id:
            add("payment_receipt", "email", "customer", customer_id, address=email)
        elif email and merchant_id:
            add("payment_receipt", "email", "merchant", merchant_id, address=email)
        if merchant_id:
            add("payment_receipt", "in_app", "merchant", merchant_id)
            merchant_email = payload.get("merchant_email")
            if merchant_email and merchant_email != email:
                add("payment_receipt", "email", "merchant", merchant_id, address=merchant_email)
        # Finance staff see invoices/AR boards — skip routine receipt fanout.

    elif event_type == DomainEventType.PAYMENT_FAILED:
        if customer_id:
            add("payment_failed", "in_app", "customer", customer_id)
        if email and customer_id:
            add("payment_failed", "email", "customer", customer_id, address=email)

    elif event_type == DomainEventType.DRIVER_ASSIGNED:
        if customer_id:
            add("driver_assigned", "in_app", "customer", customer_id)
            add("driver_assigned", "push", "customer", customer_id)
        if driver_id:
            # Loud ring on phone: high priority → ops_critical channel + sound/vibrate.
            # category=orders so prefs/grouping treat this as a job offer, not quiet tracking.
            add("job_assigned", "push", "driver", driver_id, category="orders", pri="high")
            add("job_assigned", "in_app", "driver", driver_id, category="orders", pri="high")
        if merchant_id:
            add("driver_assigned", "in_app", "merchant", merchant_id)
        # Ops board already tracks assignment — skip staff in_app spam.

    elif event_type == DomainEventType.ORDER_CANCELLED:
        if customer_id:
            add("order_cancelled", "in_app", "customer", customer_id)
            add("order_cancelled", "email", "customer", customer_id, address=email)
            add("order_cancelled", "push", "customer", customer_id)
        if driver_id:
            add("order_cancelled", "in_app", "driver", driver_id)
            add("order_cancelled", "push", "driver", driver_id)
        if merchant_id:
            add("order_cancelled", "in_app", "merchant", merchant_id)
            merchant_email = payload.get("merchant_email")
            if merchant_email:
                add("order_cancelled", "email", "merchant", merchant_id, address=merchant_email)
        add_staff("order_cancelled", "in_app", "ops")

    elif event_type == DomainEventType.DRIVER_ACCEPTED:
        if driver_id:
            add("driver_accepted", "in_app", "driver", driver_id)

    elif event_type == DomainEventType.DRIVER_REJECTED:
        add_staff("driver_rejected", "in_app", "ops")
        add_staff("driver_rejected", "push", "ops", pri="high")

    elif event_type == DomainEventType.DRIVER_ARRIVED_PICKUP:
        if customer_id:
            add("pickup_started", "push", "customer", customer_id)

    elif event_type == DomainEventType.DELIVERY_STARTED:
        if customer_id:
            add("in_transit", "push", "customer", customer_id)

    elif event_type == DomainEventType.ORDER_NEAR_DELIVERY:
        if customer_id:
            add("near_delivery", "push", "customer", customer_id)

    elif event_type == DomainEventType.PROOF_COMPLETED:
        if driver_id:
            add("pod_uploaded", "in_app", "driver", driver_id)

    elif event_type == DomainEventType.INVOICE_GENERATED:
        if customer_id and email:
            add("invoice_ready", "email", "customer", customer_id, address=email)
            add("invoice_ready", "in_app", "customer", customer_id)
        if merchant_id:
            add("merchant_invoice_ready", "in_app", "merchant", merchant_id)
            merchant_email = payload.get("merchant_email") or (email if not customer_id else None)
            if merchant_email:
                add(
                    "merchant_invoice_ready",
                    "email",
                    "merchant",
                    merchant_id,
                    address=merchant_email,
                )
        # Finance board owns invoice queue — skip staff inbox spam.

    elif event_type in (DomainEventType.MERCHANT_BILLED, "merchant.invoice_generated"):
        if merchant_id:
            add("merchant_invoice_ready", "in_app", "merchant", merchant_id)
            merchant_email = payload.get("merchant_email") or payload.get("email")
            if merchant_email:
                add(
                    "merchant_invoice_ready",
                    "email",
                    "merchant",
                    merchant_id,
                    address=merchant_email,
                )

    elif event_type in (DomainEventType.MERCHANT_APPROVED, DomainEventType.MERCHANT_ACTIVATED):
        add_staff("merchant_approved", "in_app", "ops", category="security")
        add_staff("merchant_approved", "in_app", "finance", category="security")

    elif event_type == DomainEventType.MERCHANT_SUSPENDED:
        add_staff("merchant_suspended", "in_app", "ops", category="security", pri="high")
        add_staff("merchant_suspended", "in_app", "finance", category="security", pri="high")

    elif event_type in ("merchant.closed",):
        add_staff("merchant_closed", "in_app", "ops", category="security", pri="high")
        add_staff("merchant_closed", "in_app", "finance", category="security", pri="high")
        if merchant_id:
            add("merchant_closed", "in_app", "merchant", merchant_id, category="security", pri="high")
            merchant_email = payload.get("merchant_email") or email
            if merchant_email:
                add(
                    "merchant_closed",
                    "email",
                    "merchant",
                    merchant_id,
                    address=merchant_email,
                    category="security",
                    pri="high",
                )

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
        add_staff("claim_opened", "in_app", "support")

    elif event_type == DomainEventType.CLAIM_RESOLVED:
        if customer_id:
            add("claim_updated", "in_app", "customer", customer_id)
        reporter = payload.get("driver_id")
        if reporter:
            add("claim_updated", "push", "driver", reporter, category="claims")
            add("claim_updated", "in_app", "driver", reporter, category="claims")
        add_staff("claim_updated", "in_app", "support")

    elif event_type == DomainEventType.SUPPORT_TICKET_CREATED:
        if customer_id:
            add("support_ticket_created", "in_app", "customer", customer_id)
        if email and customer_id:
            add("support_ticket_created", "email", "customer", customer_id, address=email)
        ticket_driver = payload.get("driver_id")
        if ticket_driver:
            add("support_ticket_created", "push", "driver", ticket_driver, category="support")
            add("support_ticket_created", "in_app", "driver", ticket_driver, category="support")
        add_staff("support_ticket_created", "in_app", "support")

    elif event_type in (DomainEventType.ORDER_TEMP_EXCURSION, "order.temp_excursion"):
        add_staff("temp_excursion", "email", "ops", category="orders", pri="high")
        add_staff("temp_excursion", "in_app", "ops", category="orders", pri="high")
        add_staff("temp_excursion", "push", "ops", category="orders", pri="high")
        if merchant_id:
            add("temp_excursion", "in_app", "merchant", merchant_id, category="orders", pri="high")

    elif event_type == DomainEventType.EXCEPTION_OPENED:
        ctx.setdefault("message", payload.get("exception_type") or "Delivery exception")
        ctx.setdefault("title", "Delivery exception")
        if customer_id:
            add("exception_opened", "in_app", "customer", customer_id, category="orders")
            add("exception_opened", "push", "customer", customer_id, category="orders")
        if email and customer_id:
            add("exception_opened", "email", "customer", customer_id, address=email, category="orders")
        if merchant_id:
            add("exception_opened", "in_app", "merchant", merchant_id, category="orders")
        add_staff("exception_opened", "in_app", "ops", category="orders", pri="high")
        add_staff("exception_opened", "push", "ops", category="orders", pri="high")

    elif event_type == DomainEventType.EXCEPTION_RESOLVED:
        if customer_id:
            add("exception_resolved", "in_app", "customer", customer_id, category="orders")
        if merchant_id:
            add("exception_resolved", "in_app", "merchant", merchant_id, category="orders")
        add_staff("exception_resolved", "in_app", "ops", category="orders")

    elif event_type == DomainEventType.ORDER_DELAYED:
        ctx.setdefault("message", payload.get("message") or "Your delivery is delayed")
        if customer_id:
            add("order_delayed", "in_app", "customer", customer_id, category="tracking")
            add("order_delayed", "push", "customer", customer_id, category="tracking")
        if email and customer_id:
            add("order_delayed", "email", "customer", customer_id, address=email, category="tracking")
        if merchant_id:
            add("order_delayed", "in_app", "merchant", merchant_id, category="tracking")
        add_staff("order_delayed", "in_app", "ops", category="orders", pri="high")
        add_staff("order_delayed", "push", "ops", category="orders", pri="high")

    elif event_type == DomainEventType.SLA_BREACHED:
        ctx.setdefault("message", payload.get("message") or "SLA breached")
        ctx.setdefault("title", "SLA breached")
        if customer_id:
            add("sla_breached", "in_app", "customer", customer_id, category="orders")
            add("sla_breached", "push", "customer", customer_id, category="orders")
        if email and customer_id:
            add("sla_breached", "email", "customer", customer_id, address=email, category="orders")
        if merchant_id:
            add("sla_breached", "in_app", "merchant", merchant_id, category="orders")
        add_staff("sla_breached", "in_app", "ops", category="orders", pri="critical")
        add_staff("sla_breached", "push", "ops", category="orders", pri="critical")

    elif event_type == "driver.emergency":
        add_staff("driver_alert", "in_app", "ops", category="security", pri="critical")
        add_staff("driver_alert", "push", "ops", category="security", pri="critical")

    elif event_type == "driver.route_changed":
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_route_changed", "push", "driver", did, category="tracking")
            add("driver_route_changed", "in_app", "driver", did, category="tracking")

    elif event_type == "incident.reported":
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_alert", "in_app", "driver", did, category="support")
        add_staff("driver_alert", "in_app", "ops", category="support", pri="high")
        add_staff("driver_alert", "push", "ops", category="support", pri="high")

    elif event_type in ("driver.shift_started", "driver.shift_ended", "driver.break_started", "driver.break_resumed"):
        did = payload.get("driver_id") or driver_id
        if did:
            add("driver_alert", "in_app", "driver", did, category="orders")


    return specs


def handle_domain_event(envelope: dict[str, Any]) -> None:
    event_type = envelope.get("event_type", "")
    payload = dict(envelope.get("payload") or {})
    order_id = payload.get("order_id") or (
        envelope.get("aggregate_id") if envelope.get("aggregate_type") == "order" else None
    )
    if order_id and not payload.get("order_id"):
        payload["order_id"] = order_id
    if envelope.get("aggregate_type") == "merchant":
        mid = envelope.get("aggregate_id")
        if mid and not payload.get("merchant_id"):
            payload["merchant_id"] = mid

    db = SessionLocal()
    try:
        if order_id and (
            not payload.get("customer_id")
            or not payload.get("email")
            or not payload.get("order_number")
            or not payload.get("tracking_number")
            or "is_sandbox" not in payload
            or "lang" not in payload
        ):
            payload = merge_notification_context(payload, hydrate_order_context(db, order_id))

        # Sandbox/test capacity must not clutter live in-app / email / push fans.
        if payload.get("is_sandbox") is True:
            return

        # Recipient experience: proactive consignee messages + failed-delivery policy (off by default).
        from porterchain_api.customer_experience.events import run_cx_hooks

        run_cx_hooks(db, event_type, payload)

        # The CX hook counts failed attempts; give route_table the fresh number so the
        # fallback missed-delivery email shares the per-attempt dedupe family.
        if order_id and event_type in ("order.failed", "order.delivery_failed"):
            from porterchain_api.booking_models import Order

            row = db.get(Order, order_id)
            meta = row.compliance_metadata if row is not None and isinstance(row.compliance_metadata, dict) else {}
            cx = meta.get("cx") if isinstance(meta.get("cx"), dict) else {}
            if cx.get("attempts"):
                payload["attempts"] = cx["attempts"]
        # Customer fast-book: one Send-again email after a retail delivery (CASL implied consent).
        from porterchain_api.config import get_settings
        from porterchain_api.customer_fast.mailer import enrich_send_again

        payload = enrich_send_again(db, get_settings(), event_type, payload)

        specs = _specs_for_event(event_type, payload)
        if specs:
            from porterchain_api.notification_engine.center_settings import (
                drop_matrix_off,
            )

            specs = drop_matrix_off(db, event_type, specs)
        if not specs:
            return
        specs = drop_muted_merchant_specs(db, specs)
        specs = expand_staff_specs(db, specs)
        if not specs:
            return

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


def handle_tracking_update(envelope: dict[str, Any]) -> None:
    """GPS pings are frequent: only open a DB session when the ETA is close."""
    from porterchain_api.customer_experience.events import eta_payload_is_close

    if eta_payload_is_close(dict(envelope.get("payload") or {})):
        handle_domain_event(envelope)


#: Every domain event the notification router listens to (also drives the admin matrix).
WATCHED_EVENTS: tuple[str, ...] = (
    DomainEventType.BOOKING_DRAFT_CREATED,
    DomainEventType.BOOKING_CONFIRMED,
    DomainEventType.CHECKOUT_STARTED,
    DomainEventType.PAYMENT_STARTED,
    DomainEventType.PAYMENT_SUCCEEDED,
    DomainEventType.PAYMENT_FAILED,
    DomainEventType.ORDER_CREATED,
    DomainEventType.ORDER_BOOKED,
    "merchant.booking_created",
    "order.stop_completed",
    "order.failed",
    "order.delivery_failed",
    "order.rescheduled",
    DomainEventType.CHECKOUT_ABANDONED,
    DomainEventType.DRIVER_ASSIGNED,
    DomainEventType.ORDER_CANCELLED,
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
    "merchant.invoice_generated",
    DomainEventType.MERCHANT_APPROVED,
    DomainEventType.MERCHANT_ACTIVATED,
    DomainEventType.MERCHANT_SUSPENDED,
    "merchant.closed",
    "receipt.generated",
    DomainEventType.REFUND_ISSUED,
    DomainEventType.CLAIM_OPENED,
    DomainEventType.CLAIM_RESOLVED,
    DomainEventType.SUPPORT_TICKET_CREATED,
    DomainEventType.ORDER_TEMP_EXCURSION,
    DomainEventType.EXCEPTION_OPENED,
    DomainEventType.EXCEPTION_RESOLVED,
    DomainEventType.ORDER_DELAYED,
    DomainEventType.SLA_BREACHED,
    DomainEventType.NEWSLETTER_CONFIRM_REQUESTED,
)


def register_notification_handlers() -> None:
    from porterchain_event_bus.registry import get_handler_registry

    global _notification_handlers_registered
    if _notification_handlers_registered:
        return
    _notification_handlers_registered = True

    registry = get_handler_registry()
    watched = list(WATCHED_EVENTS)
    for evt in watched:
        registry.subscribe(evt, handle_domain_event)
    for evt in ("driver.emergency", "driver.route_changed"):
        registry.subscribe(evt, handle_domain_event)
    registry.subscribe(DomainEventType.ORDER_LOCATION_UPDATED, handle_tracking_update)
    for evt in (
        "incident.reported",
        "driver.shift_started",
        "driver.shift_ended",
        "driver.break_started",
        "driver.break_resumed",
    ):
        registry.subscribe(evt, handle_domain_event)
