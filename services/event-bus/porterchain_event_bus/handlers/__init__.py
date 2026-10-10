"""Built-in event handlers — modules communicate only via events."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_event_bus.registry import get_handler_registry
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)

_default_handlers_registered = False


def register_default_handlers() -> None:
    """Wire cross-module reactions. Idempotent — safe to call multiple times."""
    global _default_handlers_registered
    if _default_handlers_registered:
        return
    _default_handlers_registered = True

    registry = get_handler_registry()

    registry.subscribe(DomainEventType.ORDER_DISPATCH_READY, _handle_order_dispatch_ready)
    registry.subscribe(DomainEventType.PAYMENT_SUCCEEDED, _handle_payment_succeeded)
    registry.subscribe(DomainEventType.PROOF_COMPLETED, _handle_pod_completed_invoice)
    registry.subscribe(DomainEventType.WEBHOOK_RECEIVED, _handle_webhook_received)
    registry.subscribe(DomainEventType.NOTIFICATION_QUEUED, _handle_notification_queued)
    registry.subscribe("order.*", _handle_merchant_webhook_fanout)
    registry.subscribe(DomainEventType.PARCEL_PICKED_UP, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.DELIVERY_STARTED, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.PARCEL_DELIVERED, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.ORDER_NEAR_DELIVERY, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.ORDER_DELAYED, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.EXCEPTION_OPENED, _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.PROOF_COMPLETED, _handle_shopify_fulfillment)
    # Failed delivery -> Shopify FAILURE event (state-machine event types, not in the catalog).
    registry.subscribe("order.failed", _handle_shopify_fulfillment)
    registry.subscribe("order.delivery_failed", _handle_shopify_fulfillment)
    registry.subscribe(DomainEventType.ORDER_CANCELLED, _handle_shopify_fulfillment_cancel)

    from porterchain_api.notification_engine.event_router import register_notification_handlers

    register_notification_handlers()


def _handle_order_dispatch_ready(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    # Precompute ranked driver suggestions (Valhalla matrix + filters) for the queue UI.
    order_id = envelope.get("aggregate_id")
    if order_id:
        get_queue_publisher().enqueue(
            QueueName.DISPATCH,
            {"action": "score_suggestions", "order_id": order_id},
        )


def _handle_payment_succeeded(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.BILLING,
        {"action": "payment_settled", "aggregate_id": envelope["aggregate_id"], "payload": envelope.get("payload", {})},
    )


def _handle_pod_completed_invoice(envelope: dict[str, Any]) -> None:
    """Enqueue POD invoice finalize — never run InvoiceService on consume_once."""
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.BILLING,
        {"action": "finalize_after_pod", "order_id": order_id},
    )


def _handle_webhook_received(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(QueueName.WEBHOOKS, envelope.get("payload", {}))


def _handle_notification_queued(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    payload = envelope.get("payload", {})
    channel = payload.get("channel", "email")
    lane = payload.get("lane")
    if lane == "fast":
        queue = QueueName.NOTIFY_FAST
    elif lane == "slow":
        queue = QueueName.NOTIFY_SLOW
    else:
        queue_map = {"email": QueueName.EMAILS, "sms": QueueName.SMS, "push": QueueName.PUSH}
        queue = queue_map.get(channel, QueueName.EMAILS)
    get_queue_publisher().enqueue(queue, payload)


def _handle_merchant_webhook_fanout(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.WEBHOOKS,
        {"action": "merchant_fanout", "event_type": envelope["event_type"], "envelope": envelope},
    )


def _handle_shopify_fulfillment(envelope: dict[str, Any]) -> None:
    """Enqueue Shopify fulfillment off consume_once (no 15s httpx on the event bus)."""
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.WEBHOOKS,
        {
            "action": "shopify_fulfillment",
            "order_id": order_id,
            "event_type": envelope.get("event_type"),
        },
    )


def _handle_shopify_fulfillment_cancel(envelope: dict[str, Any]) -> None:
    order_id = envelope.get("aggregate_id")
    if not order_id:
        return
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.WEBHOOKS,
        {"action": "shopify_fulfillment_cancel", "order_id": order_id},
    )
