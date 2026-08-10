"""Dispatch service — trigger Fleetbase dispatch actions."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler

logger = logging.getLogger(__name__)


class DispatchService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def dispatch(self, fleetbase_order_id: str, *, driver_id: str | None = None) -> dict[str, Any] | None:
        """Assign driver (PUT ``driver``) then PATCH /dispatch.

        Fleetbase public API rejects PATCH on the order resource. Assignment must
        use PUT with ``driver`` (``driver_assigned`` is read-shaped and does not
        persist). Dispatch alone returns ``No driver assigned to dispatch!`` if
        the order has no driver.
        """
        try:
            if driver_id:
                self.client.put(
                    f"/v1/orders/{fleetbase_order_id}",
                    json={"driver": driver_id},
                )
            body: dict[str, Any] = {"driver": driver_id} if driver_id else {}
            return self.client.patch(
                f"/v1/orders/{fleetbase_order_id}/dispatch",
                json=body or None,
            )
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase dispatch failed for {fleetbase_order_id}")
            return None

    def schedule(self, fleetbase_order_id: str, scheduled_at: str) -> dict[str, Any] | None:
        try:
            return self.client.patch(
                f"/v1/orders/{fleetbase_order_id}/schedule",
                json={"scheduled_at": scheduled_at},
            )
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase schedule failed for {fleetbase_order_id}")
            return None

    def start(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.post(f"/v1/orders/{fleetbase_order_id}/start")
        except Exception as exc:
            self.errors.log_and_suppress(exc, f"Fleetbase start failed for {fleetbase_order_id}")
            return None

    def complete(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        """Mark order completed in Fleetbase.

        Prefer POST /complete. Multi-stop orders often return
        ``Not all waypoints completed`` from that endpoint; fall back to
        PUT ``status=completed`` which Fleetbase accepts for ops/dev closure.
        """
        try:
            return self.client.post(f"/v1/orders/{fleetbase_order_id}/complete")
        except Exception as exc:
            msg = str(exc)
            if "waypoints completed" in msg.lower() or "not all waypoints" in msg.lower():
                try:
                    return self.client.put(
                        f"/v1/orders/{fleetbase_order_id}",
                        json={"status": "completed"},
                    )
                except Exception as fallback_exc:
                    self.errors.log_and_suppress(
                        fallback_exc,
                        f"Fleetbase complete fallback failed for {fleetbase_order_id}",
                    )
                    return None
            self.errors.log_and_suppress(exc, f"Fleetbase complete failed for {fleetbase_order_id}")
            return None

    def assign_driver(self, fleetbase_order_id: str, fleetbase_driver_id: str) -> dict[str, Any] | None:
        return self.dispatch(fleetbase_order_id, driver_id=fleetbase_driver_id)
