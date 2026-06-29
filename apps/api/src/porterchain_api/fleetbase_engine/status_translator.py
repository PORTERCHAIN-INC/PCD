"""StatusTranslator — maps Fleetbase order events/statuses ↔ Porterchain states.

Fleetbase owns operational execution; Porterchain owns the canonical order state
machine. This translator is the single place that reconciles the two vocabularies.
"""

from __future__ import annotations

from porterchain_api.domain.states import OrderState

# Fleetbase event / activity code → Porterchain OrderState.
FLEETBASE_EVENT_TO_STATE: dict[str, OrderState] = {
    # dispatch lifecycle
    "order.dispatched": OrderState.DISPATCH_READY,
    "order.ready": OrderState.DISPATCH_READY,
    "order.driver_assigned": OrderState.DRIVER_ASSIGNED,
    "order.assigned": OrderState.DRIVER_ASSIGNED,
    "driver.assigned": OrderState.DRIVER_ASSIGNED,
    "order.accepted": OrderState.DRIVER_ACCEPTED,
    "driver.accepted": OrderState.DRIVER_ACCEPTED,
    "order.started": OrderState.DRIVER_EN_ROUTE,
    "driver.enroute": OrderState.DRIVER_EN_ROUTE,
    "order.en_route": OrderState.DRIVER_EN_ROUTE,
    "order.arrived_pickup": OrderState.AT_PICKUP,
    "order.at_pickup": OrderState.AT_PICKUP,
    "order.picked_up": OrderState.PICKED_UP,
    "order.loaded": OrderState.PICKED_UP,
    "order.in_transit": OrderState.IN_TRANSIT,
    "order.arrived_dropoff": OrderState.AT_DESTINATION,
    "order.at_dropoff": OrderState.AT_DESTINATION,
    "order.near_delivery": OrderState.AT_DESTINATION,
    "order.completed": OrderState.DELIVERED,
    "order.delivered": OrderState.DELIVERED,
    "order.pod_completed": OrderState.POD_COMPLETED,
    "proof.uploaded": OrderState.POD_COMPLETED,
    # exceptions
    "order.canceled": OrderState.CANCELLED,
    "order.cancelled": OrderState.CANCELLED,
    "order.failed": OrderState.FAILED,
    "order.delivery_failed": OrderState.FAILED,
    "order.returned": OrderState.RETURN_TO_SENDER,
    "order.return_to_sender": OrderState.RETURN_TO_SENDER,
    "order.damaged": OrderState.DAMAGED,
    "order.lost": OrderState.LOST,
    "order.claim_open": OrderState.CLAIM_OPEN,
}

# Raw Fleetbase order status strings (when no explicit event) → state.
FLEETBASE_STATUS_TO_STATE: dict[str, OrderState] = {
    "created": OrderState.DISPATCH_READY,
    "dispatched": OrderState.DISPATCH_READY,
    "assigned": OrderState.DRIVER_ASSIGNED,
    "accepted": OrderState.DRIVER_ACCEPTED,
    "started": OrderState.DRIVER_EN_ROUTE,
    "enroute": OrderState.DRIVER_EN_ROUTE,
    "driver_enroute": OrderState.DRIVER_EN_ROUTE,
    "arrived": OrderState.AT_PICKUP,
    "picked_up": OrderState.PICKED_UP,
    "in_transit": OrderState.IN_TRANSIT,
    "completed": OrderState.DELIVERED,
    "delivered": OrderState.DELIVERED,
    "canceled": OrderState.CANCELLED,
    "cancelled": OrderState.CANCELLED,
    "failed": OrderState.FAILED,
    "returned": OrderState.RETURN_TO_SENDER,
    "damaged": OrderState.DAMAGED,
    "lost": OrderState.LOST,
}

# Event kinds the WebhookProcessor branches on.
TRACKING_EVENTS = {"order.location", "driver.location", "order.tracking", "tracking.updated"}
POD_EVENTS = {"order.pod_completed", "proof.uploaded", "order.completed", "order.delivered"}
CLAIM_EVENTS = {"claim.open", "claim.opened", "order.claim_open", "claim.updated"}
EXCEPTION_EVENTS = {
    "order.failed", "order.delivery_failed", "order.returned",
    "order.return_to_sender", "order.damaged", "order.lost", "order.canceled", "order.cancelled",
}
ASSIGNMENT_EVENTS = {"order.driver_assigned", "order.assigned", "driver.assigned"}


class StatusTranslator:
    @staticmethod
    def to_state(*, event: str | None = None, status: str | None = None) -> OrderState | None:
        if event:
            mapped = FLEETBASE_EVENT_TO_STATE.get(event.lower())
            if mapped:
                return mapped
        if status:
            return FLEETBASE_STATUS_TO_STATE.get(status.lower())
        return None

    @staticmethod
    def classify(event: str | None) -> str:
        """Return the WebhookProcessor branch for a Fleetbase event."""
        e = (event or "").lower()
        if e in CLAIM_EVENTS:
            return "claim"
        if e in TRACKING_EVENTS:
            return "tracking"
        if e in ASSIGNMENT_EVENTS:
            return "driver"
        if e in EXCEPTION_EVENTS:
            return "exception"
        if e in POD_EVENTS:
            return "pod"
        return "status"

    @staticmethod
    def exception_type(event: str | None) -> str:
        e = (event or "").lower()
        if "damaged" in e:
            return "PARCEL_DAMAGED"
        if "lost" in e:
            return "PARCEL_LOST"
        if "return" in e:
            return "RETURN_TO_SENDER"
        if "cancel" in e:
            return "DRIVER_CANCEL"
        return "FAILED_DELIVERY"
