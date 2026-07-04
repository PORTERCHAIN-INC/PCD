"""Event translator — Fleetbase events → Porterchain domain state."""

from __future__ import annotations

from typing import Any

from porterchain_fleetbase_adapter.events.lifecycle import FleetbaseLifecycleTranslator

FLEETBASE_EVENT_TO_ORDER_STATE: dict[str, str] = {
    k: FleetbaseLifecycleTranslator.to_state_str(event=k) or v
    for k, v in {
        "order.dispatched": "DISPATCH_READY",
        "order.driver_assigned": "DRIVER_ASSIGNED",
        "order.started": "DRIVER_EN_ROUTE",
        "order.completed": "DELIVERED",
        "order.canceled": "CANCELLED",
        "order.cancelled": "CANCELLED",
        "order.failed": "FAILED",
        "order.ready": "DISPATCH_READY",
    }.items()
}

FLEETBASE_EVENT_TO_DOMAIN_EVENT: dict[str, str] = {
    "order.dispatched": "order.driver_assigned",
    "order.driver_assigned": "order.driver_assigned",
    "order.assigned": "order.driver_assigned",
    "driver.assigned": "order.driver_assigned",
    "order.accepted": "order.driver_accepted",
    "driver.accepted": "order.driver_accepted",
    "order.started": "order.in_transit",
    "driver.enroute": "order.in_transit",
    "order.en_route": "order.in_transit",
    "order.arrived_pickup": "order.arrived_pickup",
    "order.at_pickup": "order.arrived_pickup",
    "order.picked_up": "order.pickup_completed",
    "order.loaded": "order.pickup_completed",
    "order.in_transit": "order.in_transit",
    "order.arrived_dropoff": "order.near_delivery",
    "order.at_dropoff": "order.near_delivery",
    "order.near_delivery": "order.near_delivery",
    "order.completed": "order.delivered",
    "order.delivered": "order.delivered",
    "order.pod_completed": "order.pod_completed",
    "proof.uploaded": "order.pod_completed",
    "order.canceled": "order.cancelled",
    "order.cancelled": "order.cancelled",
    "order.failed": "order.failed",
    "order.returned": "refund.requested",
    "order.return_to_sender": "refund.requested",
}


class EventTranslator:
    """Map Fleetbase webhook events to Porterchain order states and domain events."""

    def resolve_order_state(self, event_name: str) -> str | None:
        return FleetbaseLifecycleTranslator.to_state_str(event=event_name)

    def resolve_domain_event(self, event_name: str) -> str | None:
        return FLEETBASE_EVENT_TO_DOMAIN_EVENT.get(event_name)

    def extract_porterchain_order_id(self, resource: dict[str, Any]) -> str | None:
        meta = resource.get("meta")
        if isinstance(meta, dict):
            pc_id = meta.get("porterchain_order_id")
            if pc_id:
                return str(pc_id)
        internal = resource.get("internal_id")
        if internal and isinstance(internal, str):
            return internal
        return None

    def extract_fleetbase_order_id(self, resource: dict[str, Any]) -> str | None:
        for key in ("uuid", "id", "public_id"):
            val = resource.get(key)
            if val:
                return str(val)
        return None

    def translate_status(self, status: str | None) -> str | None:
        if not status:
            return None
        return FleetbaseLifecycleTranslator.to_state_str(status=status)


# Backward-compatible module-level functions
def resolve_order_state(event_name: str) -> str | None:
    return EventTranslator().resolve_order_state(event_name)


def resolve_domain_event(event_name: str) -> str | None:
    return EventTranslator().resolve_domain_event(event_name)


def extract_porterchain_order_id(resource: dict[str, Any]) -> str | None:
    return EventTranslator().extract_porterchain_order_id(resource)


def extract_fleetbase_order_id(resource: dict[str, Any]) -> str | None:
    return EventTranslator().extract_fleetbase_order_id(resource)
