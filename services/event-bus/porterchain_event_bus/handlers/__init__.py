"""Built-in event handlers — modules communicate only via events."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_event_bus.registry import get_handler_registry
from porterchain_shared.events.catalog import DomainEventType

logger = logging.getLogger(__name__)


def register_default_handlers() -> None:
    """Wire cross-module reactions. Safe to call multiple times (handlers stack)."""
    registry = get_handler_registry()

    registry.subscribe(DomainEventType.ORDER_DISPATCH_READY, _handle_order_dispatch_ready)
    registry.subscribe(DomainEventType.DRIVER_ASSIGNED, _handle_driver_assigned)
    registry.subscribe(DomainEventType.ORDER_BOOKED, _handle_order_booked_notifications)
    registry.subscribe(DomainEventType.BOOKING_CONFIRMED, _handle_booking_confirmed_notifications)
    registry.subscribe(DomainEventType.PAYMENT_SUCCEEDED, _handle_payment_succeeded)
    registry.subscribe(DomainEventType.WEBHOOK_RECEIVED, _handle_webhook_received)
    registry.subscribe(DomainEventType.NOTIFICATION_QUEUED, _handle_notification_queued)
    registry.subscribe("order.*", _handle_merchant_webhook_fanout)


def _handle_order_dispatch_ready(envelope: dict[str, Any]) -> None:
    """Fleetbase sync — reacts to dispatch ready, not direct service calls."""
    from porterchain_api.booking_engine.fleetbase_sync_handler import sync_order_from_event

    sync_order_from_event(envelope)


def _handle_driver_assigned(envelope: dict[str, Any]) -> None:
    from porterchain_api.booking_engine.fleetbase_sync_handler import sync_driver_assignment_from_event

    sync_driver_assignment_from_event(envelope)


def _handle_order_booked_notifications(envelope: dict[str, Any]) -> None:
    from porterchain_api.booking_engine.notification_handler import notify_order_booked

    notify_order_booked(envelope)


def _handle_booking_confirmed_notifications(envelope: dict[str, Any]) -> None:
    from porterchain_api.booking_engine.notification_handler import notify_booking_confirmed

    notify_booking_confirmed(envelope)


def _handle_payment_succeeded(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(
        QueueName.BILLING,
        {"action": "payment_settled", "aggregate_id": envelope["aggregate_id"], "payload": envelope.get("payload", {})},
    )


def _handle_webhook_received(envelope: dict[str, Any]) -> None:
    from porterchain_api.booking_engine.fleetbase_sync_handler import apply_fleetbase_webhook_from_event

    apply_fleetbase_webhook_from_event(envelope)

    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    get_queue_publisher().enqueue(QueueName.WEBHOOKS, envelope.get("payload", {}))


def _handle_notification_queued(envelope: dict[str, Any]) -> None:
    from porterchain_shared.queue.names import QueueName
    from porterchain_shared.queue.publisher import get_queue_publisher

    payload = envelope.get("payload", {})
    channel = payload.get("channel", "email")
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
