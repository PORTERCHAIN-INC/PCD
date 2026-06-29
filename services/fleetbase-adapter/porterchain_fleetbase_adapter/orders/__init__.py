"""Order service — Porterchain commercial order → Fleetbase operational order."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient, extract_resource_id
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.mappers import build_order_payload

logger = logging.getLogger(__name__)


class OrderService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def create_or_update(self, order: dict[str, Any]) -> str | None:
        """Push order to Fleetbase. Returns Fleetbase order id."""
        fleetbase_id = order.get("fleetbase_order_id")
        body = build_order_payload(order, company_uuid=self.settings.company_uuid or None)

        try:
            if fleetbase_id:
                response = self.client.put(f"/v1/orders/{fleetbase_id}", json=body)
            else:
                response = self.client.post("/v1/orders", json=body)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase order sync failed")
            return None

        return extract_resource_id(response, "order") or fleetbase_id

    def get(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/orders/{fleetbase_order_id}")
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase order fetch failed")
            return None

    def cancel(self, fleetbase_order_id: str) -> bool:
        try:
            self.client.delete(f"/v1/orders/{fleetbase_order_id}/cancel")
            return True
        except Exception:
            try:
                self.client.delete(f"/v1/orders/{fleetbase_order_id}")
                return True
            except Exception as exc:
                self.errors.log_and_suppress(exc, "Fleetbase order cancel failed")
                return False
