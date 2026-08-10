"""TrackingFacade — single pull + normalize path for Fleetbase order tracking.

Every portal (admin, merchant, customer, public website) must read live
tracking through this facade so all surfaces show the same normalized state,
location, ETA, and activity. Raw fetch goes through the adapter bridge only;
payload normalization lives here exactly once (previously duplicated in
booking_engine and merchant_engine, with admin reading raw payloads).
"""

from __future__ import annotations

from typing import Any

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine.integration_bridge import FleetbaseIntegrationBridge
from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_api.models import Order


class TrackingFacade:
    def __init__(self, bridge: FleetbaseIntegrationBridge | None = None) -> None:
        self._bridge = bridge or FleetbaseIntegrationBridge()

    def fetch_raw(self, settings: Settings, order: Order) -> dict[str, Any] | None:
        """Pull the raw Fleetbase tracker payload via the adapter (or None)."""
        return self._bridge.fetch_tracking(settings, order)

    @staticmethod
    def translate_live(live_raw: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize any Fleetbase live payload shape (tracker/coordinates/eta/driver)."""
        if not live_raw:
            return TrackingTranslator.translate(None)
        tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
        coords = live_raw.get("coordinates")
        merged = {**tracker, **(coords if isinstance(coords, dict) else {})}
        for key in ("eta", "driver", "status"):
            if live_raw.get(key):
                merged[key] = live_raw[key]
        return TrackingTranslator.translate(merged)

    def live_snapshot(self, settings: Settings, order: Order) -> dict[str, Any]:
        """Fetch + normalize in one call — the canonical portal snapshot."""
        return self.translate_live(self.fetch_raw(settings, order))
