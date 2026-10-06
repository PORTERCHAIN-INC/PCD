"""TrackingFacade — single normalize path for live order tracking.

Every portal (admin, merchant, customer, public website) reads live tracking
through this facade. Prefer the assigned driver's Redis ``last_known`` pin.
Ops-mirror tracker payloads are a legacy fallback when a Fleetbase order id
still has mirrored data.
"""

from __future__ import annotations

from typing import Any

from porterchain_api.config import Settings
from porterchain_api.dispatch_engine import ops_mirror
from porterchain_api.booking_engine.tracking_translator import TrackingTranslator
from porterchain_api.booking_models import Order


class TrackingFacade:
    def fetch_raw(self, settings: Settings, order: Order) -> dict[str, Any] | None:
        """Build a tracker-shaped payload from last_known, else ops mirror."""
        del settings
        known = self._last_known_for_order(order)
        if known is not None:
            return {
                "location": {"lat": known.lat, "lng": known.lng},
                "coordinates": {"lat": known.lat, "lng": known.lng},
                "recorded_at": known.recorded_at.isoformat(),
                "heading": known.heading,
                "speed": known.speed_mps,
                "source": "last_known",
                "driver_id": known.driver_id,
            }
        if not order.fleetbase_order_id:
            return None
        payload, _source = ops_mirror.read_tracking(order.fleetbase_order_id)
        return payload

    @staticmethod
    def _last_known_for_order(order: Order) -> Any:
        driver_id = getattr(order, "assigned_driver_id", None)
        if not driver_id:
            return None
        try:
            from porterchain_api.platform.last_known import read_last_known

            return read_last_known(str(driver_id))
        except Exception:
            return None

    @staticmethod
    def translate_live(live_raw: dict[str, Any] | None) -> dict[str, Any]:
        """Normalize any live payload shape (tracker/coordinates/eta/driver)."""
        if not live_raw:
            return TrackingTranslator.translate(None)
        tracker = live_raw.get("tracker") if isinstance(live_raw.get("tracker"), dict) else live_raw
        coords = live_raw.get("coordinates")
        merged = {**tracker, **(coords if isinstance(coords, dict) else {})}
        for key in ("eta", "driver", "status", "location", "recorded_at", "source"):
            if live_raw.get(key) is not None:
                merged[key] = live_raw[key]
        # last_known shape already has location
        if "location" not in merged and merged.get("lat") is not None and merged.get("lng") is not None:
            merged["location"] = {"lat": merged["lat"], "lng": merged["lng"]}
        return TrackingTranslator.translate(merged)

    def live_snapshot(self, settings: Settings, order: Order) -> dict[str, Any]:
        """Canonical portal snapshot — last_known first."""
        return self.translate_live(self.fetch_raw(settings, order))
