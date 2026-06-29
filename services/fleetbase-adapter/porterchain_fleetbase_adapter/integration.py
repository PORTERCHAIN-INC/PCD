"""Fleetbase adapter facade — single entry for Porterchain API."""

from __future__ import annotations

import logging
from typing import Any

from porterchain_fleetbase_adapter.auth import FleetbaseSsoClient
from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.dispatch import DispatchService
from porterchain_fleetbase_adapter.drivers import DriverService
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.events import EventTranslator
from porterchain_fleetbase_adapter.orders import OrderService
from porterchain_fleetbase_adapter.pod import PodService
from porterchain_fleetbase_adapter.routes import RouteService
from porterchain_fleetbase_adapter.tracking import TrackingService
from porterchain_fleetbase_adapter.vehicles import VehicleService
from porterchain_fleetbase_adapter.webhooks import WebhookService

logger = logging.getLogger(__name__)


class FleetbaseAdapter:
    """
    Porterchain logistics engine bridge.

    Website / portals → Porterchain API → this adapter → Fleetbase API
    """

    def __init__(self, settings: FleetbaseSettings | None = None) -> None:
        self.settings = settings or FleetbaseSettings()
        self.errors = ErrorHandler()
        self.client = FleetbaseClient(self.settings, error_handler=self.errors)
        self.orders = OrderService(self.settings, self.client, self.errors)
        self.drivers = DriverService(self.settings, self.client, self.errors)
        self.vehicles = VehicleService(self.settings, self.client, self.errors)
        self.dispatch = DispatchService(self.settings, self.client, self.errors)
        self.tracking = TrackingService(self.settings, self.client, self.errors)
        self.routes = RouteService(self.settings, self.client, self.errors)
        self.pod = PodService(self.settings, self.client, self.errors)
        self.events = EventTranslator()
        self.webhooks = WebhookService(
            webhook_secret=self.settings.webhook_secret,
            api_key=self.settings.api_key,
            translator=self.events,
        )
        self.sso = FleetbaseSsoClient(self.settings, client=self.client, error_handler=self.errors)

    @property
    def is_enabled(self) -> bool:
        return self.settings.is_enabled

    # --- Order sync ---

    def sync_order(self, order: dict[str, Any]) -> str | None:
        return self.orders.create_or_update(order)

    # --- Driver sync ---

    def sync_driver(self, driver: dict[str, Any]) -> str | None:
        return self.drivers.sync(driver)

    # --- Vehicle sync ---

    def sync_vehicle(self, vehicle: dict[str, Any]) -> str | None:
        return self.vehicles.sync(vehicle)

    # --- Tracking sync ---

    def fetch_tracking(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        snapshot = self.tracking.build_tracking_snapshot(fleetbase_order_id)
        if not snapshot:
            return None
        snapshot["proofs"] = self.pod.fetch_proofs(fleetbase_order_id)
        return snapshot

    # --- Dispatch sync ---

    def sync_dispatch(self, fleetbase_order_id: str, *, driver_id: str | None = None) -> dict[str, Any] | None:
        return self.dispatch.dispatch(fleetbase_order_id, driver_id=driver_id)

    # --- Status sync (from webhook) ---

    def process_webhook(
        self,
        payload: bytes,
        body: dict[str, Any],
        *,
        signature: str | None = None,
    ) -> dict[str, Any] | None:
        return self.webhooks.process(payload, body, signature=signature)

    # --- Proof sync ---

    def sync_proofs(self, fleetbase_order_id: str) -> list[dict[str, Any]]:
        return self.pod.fetch_proofs(fleetbase_order_id)

    def sync_status_from_fleetbase(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        """Poll Fleetbase for current order status (fallback to webhooks)."""
        order_data = self.orders.get(fleetbase_order_id)
        if not order_data:
            return None
        resource = order_data.get("order") if isinstance(order_data.get("order"), dict) else order_data
        status = resource.get("status") if isinstance(resource, dict) else None
        return {
            "fleetbase_order_id": fleetbase_order_id,
            "status": status,
            "target_state": self.events.translate_status(status),
            "resource": resource,
            "proofs": self.sync_proofs(fleetbase_order_id),
        }

    # --- Route sync ---

    def fetch_route(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        tracker = self.tracking.fetch_tracker(fleetbase_order_id)
        if not tracker:
            return self.routes.distance_and_time(fleetbase_order_id)
        route = self.routes.extract_route_from_tracker(tracker)
        if route:
            return route
        return self.routes.distance_and_time(fleetbase_order_id)

    # --- Driver platform extensions (extends Fleetbase, does not replace) ---

    def track_driver_location(
        self,
        fleetbase_driver_id: str,
        *,
        lat: float,
        lng: float,
        heading: float | None = None,
        speed: float | None = None,
    ) -> bool:
        return self.drivers.track_location(
            fleetbase_driver_id, lat=lat, lng=lng, heading=heading, speed=speed
        )

    def toggle_driver_online(self, fleetbase_driver_id: str, *, online: bool) -> bool:
        return self.drivers.toggle_online(fleetbase_driver_id, online=online)

    def upload_pod_photo(self, fleetbase_order_id: str, file_url: str) -> bool:
        return self.pod.upload_photo(fleetbase_order_id, file_url)

    def upload_pod_signature(self, fleetbase_order_id: str, signature_data: str) -> bool:
        return self.pod.upload_signature(fleetbase_order_id, signature_data)

    def upload_pod_barcode(self, fleetbase_order_id: str, barcode: str) -> bool:
        return self.pod.upload_barcode(fleetbase_order_id, barcode)


# Backward-compatible alias
FleetbaseIntegrationService = FleetbaseAdapter
