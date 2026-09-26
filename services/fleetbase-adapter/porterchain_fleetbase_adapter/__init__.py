"""Porterchain ↔ Fleetbase adapter — sole integration boundary."""

from porterchain_fleetbase_adapter.client import FleetbaseClient, extract_resource_id
from porterchain_fleetbase_adapter.config import FleetbaseSettings
from porterchain_fleetbase_adapter.dispatch import DispatchService
from porterchain_fleetbase_adapter.drivers import DriverService
from porterchain_fleetbase_adapter.errors import ErrorHandler
from porterchain_fleetbase_adapter.events import EventTranslator
from porterchain_fleetbase_adapter.integration import FleetbaseAdapter, FleetbaseIntegrationService
from porterchain_fleetbase_adapter.manifests import ManifestService
from porterchain_fleetbase_adapter.orders import OrderService
from porterchain_fleetbase_adapter.orchestrator import OrchestratorService
from porterchain_fleetbase_adapter.pod import PodService
from porterchain_fleetbase_adapter.retry import RetryPolicy
from porterchain_fleetbase_adapter.routes import RouteService
from porterchain_fleetbase_adapter.tracking import TrackingService
from porterchain_fleetbase_adapter.vehicles import FleetbaseVehicleService, VehicleService
from porterchain_fleetbase_adapter.webhooks import WebhookService

__all__ = [
    "DispatchService",
    "DriverService",
    "ErrorHandler",
    "EventTranslator",
    "FleetbaseAdapter",
    "FleetbaseClient",
    "FleetbaseIntegrationService",
    "FleetbaseSettings",
    "FleetbaseVehicleService",
    "ManifestService",
    "OrderService",
    "OrchestratorService",
    "PodService",
    "RetryPolicy",
    "RouteService",
    "TrackingService",
    "VehicleService",
    "WebhookService",
    "extract_resource_id",
]
