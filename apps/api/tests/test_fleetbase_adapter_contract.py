"""Lifecycle maps live in PorterChain. The Fleetbase adapter is gone."""

from __future__ import annotations

from porterchain_api.domain.order_lifecycle import (
    FLEETBASE_EVENT_TO_STATE,
    FLEETBASE_STATUS_TO_STATE,
    FleetbaseLifecycleTranslator,
)


def test_fleetbase_event_maps_to_porterchain_state():
    assert FLEETBASE_EVENT_TO_STATE["order.delivered"] == "DELIVERED"
    assert FLEETBASE_EVENT_TO_STATE["order.driver_assigned"] == "DRIVER_ASSIGNED"
    assert FLEETBASE_STATUS_TO_STATE["in_transit"] == "IN_TRANSIT"


def test_lifecycle_resolves_order_state():
    assert FleetbaseLifecycleTranslator.to_state_str(event="order.delivered") == "DELIVERED"
