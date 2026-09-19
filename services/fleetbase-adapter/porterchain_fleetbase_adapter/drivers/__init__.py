"""Driver service — Porterchain driver partner → Fleetbase driver."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.client import FleetbaseClient, extract_resource_id
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.mappers import build_driver_payload

logger = logging.getLogger(__name__)


class DriverService:
    def __init__(
        self,
        settings: FleetbaseSettings,
        client: FleetbaseClient | None = None,
        error_handler: ErrorHandler | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or FleetbaseClient(settings)
        self.errors = error_handler or ErrorHandler()

    def sync(self, driver: dict[str, Any]) -> str | None:
        fleetbase_id = driver.get("fleetbase_driver_id")
        body = build_driver_payload(driver, company_uuid=self.settings.company_uuid or None)

        try:
            if fleetbase_id:
                response = self.client.put(f"/v1/drivers/{fleetbase_id}", json=body)
            else:
                response = self.client.post("/v1/drivers", json=body)
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase driver sync failed")
            return None

        resolved = extract_resource_id(response, "driver") or fleetbase_id
        vehicle_public_id = driver.get("fleetbase_vehicle_id")
        if resolved and isinstance(vehicle_public_id, str) and vehicle_public_id.startswith("vehicle_"):
            # Greedy/VROOM only treat a van as available when it has a linked driver.
            # Public ids belong on these fields — MySQL uuid FKs are omitted in the mapper.
            try:
                self.client.put(f"/v1/vehicles/{vehicle_public_id}", json={"driver": resolved})
                self.client.put(
                    f"/v1/drivers/{resolved}",
                    json={"vehicle": vehicle_public_id, "online": True},
                )
                self.client.post(f"/v1/drivers/{resolved}/toggle-online", json={"online": True})
            except Exception as exc:
                self.errors.log_and_suppress(exc, "Fleetbase driver-vehicle link failed")
        return resolved

    def get(self, fleetbase_driver_id: str) -> dict[str, Any] | None:
        try:
            return self.client.get(f"/v1/drivers/{fleetbase_driver_id}")
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase driver fetch failed")
            return None

    def list_all(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """All Fleetbase drivers (online status + last known location).

        Feeds read-only ops surfaces (live map, dispatch suggestions)."""
        try:
            response = self.client.get("/v1/drivers", params={"limit": limit})
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase driver list failed")
            return []
        if isinstance(response, dict):
            for key in ("drivers", "data", "items"):
                value = response.get(key)
                if isinstance(value, list):
                    return [v for v in value if isinstance(v, dict)]
        return []

    def track_location(
        self,
        fleetbase_driver_id: str,
        *,
        lat: float,
        lng: float,
        heading: float | None = None,
        speed: float | None = None,
    ) -> bool:
        body: dict[str, Any] = {"latitude": lat, "longitude": lng}
        if heading is not None:
            body["heading"] = heading
        if speed is not None:
            body["speed"] = speed
        try:
            self.client.post(f"/v1/drivers/{fleetbase_driver_id}/track", json=body)
            return True
        except Exception as exc:
            from porterchain_fleetbase_adapter.errors import FleetbaseApiError

            # Seed / deleted driver — nothing to track; treat as success so GPS drain
            # does not dead-letter forever.
            if isinstance(exc, FleetbaseApiError) and exc.status_code == 404:
                return True
            self.errors.log_and_suppress(exc, "Fleetbase driver track failed")
            return False

    def toggle_online(self, fleetbase_driver_id: str, *, online: bool) -> bool:
        try:
            self.client.post(f"/v1/drivers/{fleetbase_driver_id}/toggle-online", json={"online": online})
            return True
        except Exception as exc:
            self.errors.log_and_suppress(exc, "Fleetbase toggle-online failed")
            return False
