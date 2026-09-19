"""TrackingFacade — single normalize path for Fleetbase order tracking.

Every portal (admin, merchant, customer, public website) must read live
tracking through this facade so all surfaces show the same normalized state,
location, ETA, and activity. Raw payload comes from the Redis ops mirror
(worker refreshes via adapter); request threads never call Fleetbase HTTP.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.config import Settings
from porterchain_api.fleetbase_engine import ops_mirror
from porterchain_api.fleetbase_engine.tracking_translator import TrackingTranslator
from porterchain_api.booking_models import Order


class TrackingFacade:
    def fetch_raw(self, settings: Settings, order: Order) -> dict[str, Any] | None:
        """Read mirrored Fleetbase tracker payload (or None on miss)."""
        del settings  # bridge flag checked at write time by worker
        if not order.fleetbase_order_id:
            return None
        payload, _source = ops_mirror.read_tracking(order.fleetbase_order_id)
        return payload

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
        """Mirror fetch + normalize — the canonical portal snapshot."""
        return self.translate_live(self.fetch_raw(settings, order))
