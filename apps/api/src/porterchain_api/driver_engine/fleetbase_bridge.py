"""Fleetbase bridge for driver platform — extends Fleetbase via adapter."""

from __future__ import annotations

from porterchain_fleetbase_adapter.events.lifecycle import FleetbaseLifecycleTranslator

from porterchain_api.config import Settings
from porterchain_api.services.fleetbase_integration import get_fleetbase_integration


class DriverFleetbaseBridge:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._adapter = get_fleetbase_integration(settings)

    @property
    def enabled(self) -> bool:
        return bool(self._settings.fleetbase_dispatch_bridge and self._adapter.is_enabled)

    def track_driver_location(
        self, fleetbase_driver_id: str, *, lat: float, lng: float, heading: float | None = None, speed: float | None = None
    ) -> bool:
        if not self.enabled:
            return False
        return self._adapter.track_driver_location(
            fleetbase_driver_id, lat=lat, lng=lng, heading=heading, speed=speed
        )

    def toggle_driver_online(self, fleetbase_driver_id: str, *, online: bool) -> bool:
        if not self.enabled:
            return False
        return self._adapter.toggle_driver_online(fleetbase_driver_id, online=online)

    def fetch_route(self, fleetbase_order_id: str) -> dict | None:
        if not self.enabled:
            return None
        return self._adapter.fetch_route(fleetbase_order_id)

    def upload_pod_photo(self, fleetbase_order_id: str, file_url: str) -> bool:
        if not self.enabled:
            return False
        return self._adapter.upload_pod_photo(fleetbase_order_id, file_url)

    def upload_pod_signature(self, fleetbase_order_id: str, signature_data: str) -> bool:
        if not self.enabled:
            return False
        return self._adapter.upload_pod_signature(fleetbase_order_id, signature_data)

    def upload_pod_barcode(self, fleetbase_order_id: str, barcode: str) -> bool:
        if not self.enabled:
            return False
        return self._adapter.upload_pod_barcode(fleetbase_order_id, barcode)

    def sync_order_state(self, fleetbase_order_id: str, order_state: str) -> bool:
        """Mirror Porterchain order state to Fleetbase execution layer."""
        if not self.enabled:
            return False
        state = order_state.upper()
        if state == "DRIVER_EN_ROUTE":
            return self._adapter.start_order_execution(fleetbase_order_id) is not None
        if state in ("DELIVERED", "POD_COMPLETED"):
            return self._adapter.complete_order_execution(fleetbase_order_id) is not None
        fleetbase_status = FleetbaseLifecycleTranslator.to_fleetbase_status(state)
        if not fleetbase_status:
            return False
        return self._adapter.update_order_status(fleetbase_order_id, fleetbase_status)
