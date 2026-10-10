"""Event schema versioning — consumers declare supported versions per event type."""

from __future__ import annotations

# Bump when payload shape changes incompatibly for a given event_type.
EVENT_SCHEMA_VERSIONS: dict[str, int] = {
    "visitor.created": 1,
    "visitor.session_started": 1,
    "visitor.session_merged": 1,
    "quote.created": 1,
    "quote.accepted": 1,
    "quote.expired": 1,
    "customer.registered": 1,
    "customer.authenticated": 1,
    "merchant.approved": 1,
    "merchant.activated": 1,
    "merchant.billed": 1,
    "payment.succeeded": 1,
    "payment.failed": 1,
    "booking.started": 1,
    "booking.confirmed": 1,
    "checkout.started": 1,
    "checkout.abandoned": 1,
    "order.created": 1,
    "order.booked": 2,
    "order.dispatch_ready": 1,
    "order.dispatch_requested": 1,
    "order.driver_assigned": 1,
    "order.driver_accepted": 1,
    "order.arrived_pickup": 1,
    "order.pickup_completed": 1,
    "order.in_transit": 1,
    "order.delivered": 1,
    "order.pod_completed": 1,
    "order.invoiced": 1,
    "order.closed": 1,
    "order.cancelled": 1,
    "driver.payout_created": 1,
    "refund.requested": 1,
    "refund.issued": 1,
    "claim.opened": 1,
    "claim.resolved": 1,
    "notification.queued": 1,
    "notification.sent": 1,
    "webhook.received": 1,
}


def schema_version_for(event_type: str) -> int:
    return EVENT_SCHEMA_VERSIONS.get(event_type, 1)
