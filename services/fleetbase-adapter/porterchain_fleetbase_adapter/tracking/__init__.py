"""Tracking service — live order status from Fleetbase."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)


class TrackingService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def fetch_tracker(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}/tracker")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase tracker fetch failed for {fleetbase_order_id}")
            return None

    def fetch_eta(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}/eta")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase ETA fetch failed for {fleetbase_order_id}")
            return None

    def build_tracking_snapshot(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        """Aggregate tracker + ETA for Porterchain tracking API."""
        tracker = self.fetch_tracker(fleetbase_order_id)
        if not tracker:
            return None
        eta = self.fetch_eta(fleetbase_order_id)
        return {
            "fleetbase_order_id": fleetbase_order_id,
            "tracker": tracker,
            "eta": eta,
            "status": tracker.get("status") or _deep_get(tracker, "order", "status"),
            "driver": tracker.get("driver") or _deep_get(tracker, "order", "driver"),
            "coordinates": tracker.get("coordinates") or tracker.get("position"),
        }


def _deep_get(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current
