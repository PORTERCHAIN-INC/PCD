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

    def run_orchestrator(
        self,
        order_ids: list[str],
        *,
        mode: str = "allocate",
        engine: str | None = None,
        vehicle_ids: list[str] | None = None,
        driver_ids: list[str] | None = None,
        options: dict[str, Any] | None = None,
        prior_assignments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any] | None:
        from porterchain_fleetbase_adapter.orchestrator import OrchestratorService

        result = OrchestratorService(self.settings, self.client, self.errors).run(
            order_ids=order_ids,
            mode=mode,
            engine=engine,
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids,
            options=options,
            prior_assignments=prior_assignments,
        )
        return result if result.get("ok") is not False or result.get("assignments") is not None else None

    def commit_orchestrator(
        self,
        assignments: list[dict[str, Any]] | None = None,
        *,
        run_id: str | None = None,
        scheduled_date: str | None = None,
    ) -> dict[str, Any] | None:
        """Commit plan assignments → Fleetbase manifests.

        Prefer `assignments` (fleetops 0.6.59 contract). `run_id` is accepted for
        backward compatibility but ignored — upstream commit requires assignments.
        """
        del run_id  # legacy keyword; commit is assignment-based
        if not assignments:
            return None
        from porterchain_fleetbase_adapter.orchestrator import OrchestratorService

        return OrchestratorService(self.settings, self.client, self.errors).commit(
            assignments=assignments, scheduled_date=scheduled_date
        )
