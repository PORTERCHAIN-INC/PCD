"""Route service — route geometry and optimization from Fleetbase."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)


class RouteService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def distance_and_time(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}/distance-and-time")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase distance matrix failed for {fleetbase_order_id}")
            return None

    def extract_route_from_tracker(self, tracker: dict[str, Any]) -> dict[str, Any] | None:
        """Pull route polyline / waypoints from tracker payload."""
        route = tracker.get("route")
        if isinstance(route, dict):
            return route
        order = tracker.get("order")
        if isinstance(order, dict) and isinstance(order.get("route"), dict):
            return order["route"]
        waypoints = tracker.get("waypoints")
        if waypoints:
            return {"waypoints": waypoints}
        return None

    def run_orchestrator(self, order_ids: list[str]) -> dict[str, Any] | None:
        try:
            return self.client.post("/v1/orchestrator/run", json={"orders": order_ids})
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase orchestrator run failed")
            return None

    def commit_orchestrator(self, run_id: str) -> dict[str, Any] | None:
        try:
            return self.client.post("/v1/orchestrator/commit", json={"run_id": run_id})
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase orchestrator commit failed")
            return None
