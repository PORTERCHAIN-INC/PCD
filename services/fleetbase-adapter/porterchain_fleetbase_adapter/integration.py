"""Fleetbase adapter facade — single entry for Porterchain API."""

from __future__ import annotations

import logging
import time
from typing import Any

from porterchain_fleetbase_adapter.auth import FleetbaseSsoClient
from porterchain_fleetbase_adapter.client import FleetbaseClient
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.dispatch import DispatchService
from porterchain_fleetbase_adapter.drivers import DriverService
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.events import EventTranslator
from porterchain_fleetbase_adapter.manifests import ManifestService
from porterchain_fleetbase_adapter.orders import OrderService
from porterchain_fleetbase_adapter.orchestrator import OrchestratorService
from porterchain_fleetbase_adapter.pod import PodService
from porterchain_fleetbase_adapter.routes import RouteService
from porterchain_fleetbase_adapter.tracking import TrackingService
from porterchain_fleetbase_adapter.vehicles import VehicleService
from porterchain_fleetbase_adapter.webhooks import WebhookService
from porterchain_fleetbase_adapter.zones import ZonesService

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
        self.zones = ZonesService(self.settings, self.client, self.errors)
        self.routes = RouteService(self.settings, self.client, self.errors)
        self.pod = PodService(self.settings, self.client, self.errors)
        self.manifests = ManifestService(self.settings, self.client, self.errors)
        self.orchestrator = OrchestratorService(self.settings, self.client, self.errors)
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

    def verify_bond(self, *, reset_circuit: bool = True) -> dict[str, Any]:
        """Authenticated handshake proving the PorterChain↔Fleetbase bond.

        Jeff Dean: treat Fleetbase as a bonded capability (adapter + company +
        API key), never fork PHP into PorterChain. A successful GET /v1/orders
        means the identity wire is live; reset the shared circuit so recovery
        is automatic after transient outages.
        """
        from porterchain_fleetbase_adapter.circuit_breaker import reset_shared_breaker

        if not self.is_enabled:
            return {"ok": False, "bonded": False, "error": "bridge_disabled"}
        if not (self.settings.api_key or "").strip():
            return {"ok": False, "bonded": False, "error": "api_key_missing"}
        if not (self.settings.company_uuid or "").strip():
            return {"ok": False, "bonded": False, "error": "company_uuid_missing"}

        started = time.monotonic()
        try:
            self.client.get("/v1/orders", params={"limit": 1})
        except Exception as exc:  # noqa: BLE001
            latency_ms = round((time.monotonic() - started) * 1000, 1)
            status_code = getattr(exc, "status_code", None)
            logger.warning(
                "fleetbase_bond_failed error=%s status=%s latency_ms=%s",
                type(exc).__name__,
                status_code,
                latency_ms,
            )
            return {
                "ok": False,
                "bonded": False,
                "error": str(exc)[:200],
                "error_type": type(exc).__name__,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "company_uuid_configured": True,
                "api_key_configured": True,
            }

        latency_ms = round((time.monotonic() - started) * 1000, 1)
        if reset_circuit:
            reset_shared_breaker(
                failure_threshold=self.settings.breaker_failure_threshold,
                open_seconds=self.settings.breaker_open_seconds,
            )
        logger.info("fleetbase_bond_ok latency_ms=%s", latency_ms)
        return {
            "ok": True,
            "bonded": True,
            "latency_ms": latency_ms,
            "company_uuid_configured": True,
            "api_key_configured": True,
        }

    # --- Order sync ---

    def sync_order(self, order: dict[str, Any]) -> str | None:
        return self.orders.create_or_update(order)

    def cancel_order(self, fleetbase_order_id: str) -> bool:
        """Cancel an operational order in Fleetbase (execution layer only)."""
        return self.orders.cancel(fleetbase_order_id)

    # --- Driver sync ---

    def sync_driver(self, driver: dict[str, Any]) -> str | None:
        return self.drivers.sync(driver)

    def list_drivers(self, *, limit: int = 200) -> list[dict[str, Any]]:
        """Live Fleetbase driver roster (online + location), read-only."""
        if not self.is_enabled:
            return []
        return self.drivers.list_all(limit=limit)

    def list_manifests(
        self,
        *,
        scheduled_date: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Committed Fleetbase manifests (orchestrator output), read-only."""
        if not self.is_enabled:
            return []
        return self.manifests.list(
            scheduled_date=scheduled_date, status=status, limit=limit
        )

    def get_manifest(self, manifest_id: str) -> dict[str, Any] | None:
        if not self.is_enabled:
            return None
        return self.manifests.get(manifest_id)

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
    ) -> dict[str, Any]:
        if not self.is_enabled:
            return {"ok": False, "error": "fleetbase_disabled", "assignments": [], "metrics": {}}
        return self.orchestrator.run(
            order_ids=order_ids,
            mode=mode,
            engine=engine,
            vehicle_ids=vehicle_ids,
            driver_ids=driver_ids,
            options=options,
            prior_assignments=prior_assignments,
        )

    def commit_orchestrator(
        self,
        assignments: list[dict[str, Any]],
        *,
        scheduled_date: str | None = None,
    ) -> dict[str, Any]:
        if not self.is_enabled:
            return {"ok": False, "error": "fleetbase_disabled", "manifests": []}
        return self.orchestrator.commit(
            assignments=assignments, scheduled_date=scheduled_date
        )

    def list_orchestrator_engines(self) -> list[dict[str, Any]]:
        if not self.is_enabled:
            return []
        return self.orchestrator.list_engines()

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

    def position_history(
        self,
        *,
        order_uuid: str | None = None,
        subject_uuid: str | None = None,
        limit: int = 500,
    ) -> dict[str, Any]:
        """REST breadcrumb trail for ops playback (never SocketCluster replay)."""
        if not self.is_enabled:
            return {"points": [], "source": "none"}
        return self.tracking.position_history(
            order_uuid=order_uuid, subject_uuid=subject_uuid, limit=limit
        )

    def list_zone_overlays(self) -> list[dict[str, Any]]:
        """Fleetbase zones / service-area polygons for map overlays."""
        if not self.is_enabled:
            return []
        return self.zones.list_overlays()

    # --- Dispatch sync ---

    def sync_dispatch(self, fleetbase_order_id: str, *, driver_id: str | None = None) -> dict[str, Any] | None:
        return self.dispatch.dispatch(fleetbase_order_id, driver_id=driver_id)

    def start_order_execution(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        return self.dispatch.start(fleetbase_order_id)

    def complete_order_execution(self, fleetbase_order_id: str) -> dict[str, Any] | None:
        return self.dispatch.complete(fleetbase_order_id)

    def update_order_status(self, fleetbase_order_id: str, status: str) -> bool:
        return self.orders.update_status(fleetbase_order_id, status)

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
