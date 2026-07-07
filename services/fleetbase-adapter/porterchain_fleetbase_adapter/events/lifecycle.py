"""Canonical Fleetbase event → Porterchain state vocabulary (adapter-owned)."""

from __future__ import annotations

FLEETBASE_EVENT_TO_STATE: dict[str, str] = {
    "order.dispatched": "DISPATCH_READY",
    "order.ready": "DISPATCH_READY",
    "order.driver_assigned": "DRIVER_ASSIGNED",
    "order.assigned": "DRIVER_ASSIGNED",
    "driver.assigned": "DRIVER_ASSIGNED",
    "order.accepted": "DRIVER_ACCEPTED",
    "driver.accepted": "DRIVER_ACCEPTED",
    "order.started": "DRIVER_EN_ROUTE",
    "driver.enroute": "DRIVER_EN_ROUTE",
    "order.en_route": "DRIVER_EN_ROUTE",
    "order.arrived_pickup": "AT_PICKUP",
    "order.at_pickup": "AT_PICKUP",
    "order.picked_up": "PICKED_UP",
    "order.loaded": "PICKED_UP",
    "order.in_transit": "IN_TRANSIT",
    "order.arrived_dropoff": "AT_DESTINATION",
    "order.at_dropoff": "AT_DESTINATION",
    "order.near_delivery": "AT_DESTINATION",
    "order.completed": "DELIVERED",
    "order.delivered": "DELIVERED",
    "order.pod_completed": "POD_COMPLETED",
    "proof.uploaded": "POD_COMPLETED",
    "order.canceled": "CANCELLED",
    "order.cancelled": "CANCELLED",
    "order.failed": "FAILED",
    "order.delivery_failed": "FAILED",
    "order.returned": "RETURN_TO_SENDER",
    "order.return_to_sender": "RETURN_TO_SENDER",
    "order.damaged": "DAMAGED",
    "order.lost": "LOST",
    "order.claim_open": "CLAIM_OPEN",
}

FLEETBASE_STATUS_TO_STATE: dict[str, str] = {
    "created": "DISPATCH_READY",
    "dispatched": "DISPATCH_READY",
    "assigned": "DRIVER_ASSIGNED",
    "accepted": "DRIVER_ACCEPTED",
    "started": "DRIVER_EN_ROUTE",
    "enroute": "DRIVER_EN_ROUTE",
    "driver_enroute": "DRIVER_EN_ROUTE",
    "arrived": "AT_PICKUP",
    "picked_up": "PICKED_UP",
    "in_transit": "IN_TRANSIT",
    "completed": "DELIVERED",
    "delivered": "DELIVERED",
    "canceled": "CANCELLED",
    "cancelled": "CANCELLED",
    "failed": "FAILED",
    "returned": "RETURN_TO_SENDER",
    "damaged": "DAMAGED",
    "lost": "LOST",
}

TRACKING_EVENTS = {"order.location", "driver.location", "order.tracking", "tracking.updated"}
POD_EVENTS = {"order.pod_completed", "proof.uploaded", "order.completed", "order.delivered"}
CLAIM_EVENTS = {"claim.open", "claim.opened", "order.claim_open", "claim.updated"}
EXCEPTION_EVENTS = {
    "order.failed", "order.delivery_failed", "order.returned",
    "order.return_to_sender", "order.damaged", "order.lost", "order.canceled", "order.cancelled",
}
ASSIGNMENT_EVENTS = {"order.driver_assigned", "order.assigned", "driver.assigned"}

# Outbound: Porterchain order state → Fleetbase operational status (masterrule Appendix A).
PORTERCHAIN_STATE_TO_FLEETBASE_STATUS: dict[str, str] = {
    "DISPATCH_READY": "pending",
    "DRIVER_ASSIGNED": "assigned",
    "DRIVER_ACCEPTED": "accepted",
    "DRIVER_EN_ROUTE": "started",
    "AT_PICKUP": "arrived",
    "PICKED_UP": "picked_up",
    "IN_TRANSIT": "in_transit",
    "AT_DESTINATION": "in_transit",
    "DELIVERED": "completed",
    "POD_COMPLETED": "completed",
    "RETURN_TO_SENDER": "returned",
    "CANCELLED": "cancelled",
    "FAILED": "failed",
}


class FleetbaseLifecycleTranslator:
    @staticmethod
    def to_state_str(*, event: str | None = None, status: str | None = None) -> str | None:
        if event:
            mapped = FLEETBASE_EVENT_TO_STATE.get(event.lower())
            if mapped:
                return mapped
        if status:
            return FLEETBASE_STATUS_TO_STATE.get(status.lower())
        return None

    @staticmethod
    def classify(event: str | None) -> str:
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
    def to_fleetbase_status(order_state: str | None) -> str | None:
        if not order_state:
            return None
        return PORTERCHAIN_STATE_TO_FLEETBASE_STATUS.get(order_state.upper())

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
