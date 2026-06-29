"""Event translator — Fleetbase events → Porterchain domain state."""

from __future__ import annotations

from typing import Any

FLEETBASE_EVENT_TO_ORDER_STATE: dict[str, str] = {
    "order.dispatched": "DRIVER_ASSIGNED",
    "order.driver_assigned": "DRIVER_ASSIGNED",
    "order.started": "PICKED_UP",
    "order.completed": "DELIVERED",
    "order.canceled": "CANCELLED",
    "order.cancelled": "CANCELLED",
    "order.failed": "FAILED",
    "order.ready": "DISPATCH_READY",
}

FLEETBASE_EVENT_TO_DOMAIN_EVENT: dict[str, str] = {
    "order.dispatched": "order.driver_assigned",
    "order.driver_assigned": "order.driver_assigned",
    "order.started": "order.pickup_completed",
    "order.completed": "order.delivered",
    "order.canceled": "order.cancelled",
    "order.cancelled": "order.cancelled",
    "order.failed": "order.failed",
}


class EventTranslator:
    """Map Fleetbase webhook events to Porterchain order states and domain events."""

    def resolve_order_state(self, event_name: str) -> str | None:
        return FLEETBASE_EVENT_TO_ORDER_STATE.get(event_name)

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
        return self.resolve_order_state(f"order.{status}")


# Backward-compatible module-level functions
def resolve_order_state(event_name: str) -> str | None:
    return EventTranslator().resolve_order_state(event_name)


def resolve_domain_event(event_name: str) -> str | None:
    return EventTranslator().resolve_domain_event(event_name)


def extract_porterchain_order_id(resource: dict[str, Any]) -> str | None:
    return EventTranslator().extract_porterchain_order_id(resource)


def extract_fleetbase_order_id(resource: dict[str, Any]) -> str | None:
    return EventTranslator().extract_fleetbase_order_id(resource)
