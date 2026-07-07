"""Vehicle service — Porterchain vehicle → Fleetbase vehicle."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient, extract_resource_id
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.mappers import build_vehicle_payload

logger = logging.getLogger(__name__)


class VehicleService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def sync(self, vehicle: dict[str, Any]) -> str | None:
        fleetbase_id = vehicle.get("fleetbase_vehicle_id")
        body = build_vehicle_payload(vehicle, company_uuid=self.settings.company_uuid or None)

        try:
            if fleetbase_id:
                response = self.client.put(f"/v1/vehicles/{fleetbase_id}", json=body)
            else:
                response = self.client.post("/v1/vehicles", json=body)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase vehicle sync failed")
            return None

        return extract_resource_id(response, "vehicle") or fleetbase_id

    def get(self, fleetbase_vehicle_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/vehicles/{fleetbase_vehicle_id}")
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase vehicle fetch failed")
            return None
