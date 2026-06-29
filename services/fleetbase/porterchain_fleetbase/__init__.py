"""Deprecated package — re-exports from porterchain_fleetbase_adapter.

Use ``porterchain_fleetbase_adapter`` (``services/fleetbase-adapter/``) for new code.
"""

from porterchain_fleetbase_adapter import *  # noqa: F403
from porterchain_fleetbase_adapter import (
    FleetbaseAdapter,
    FleetbaseClient,
    FleetbaseIntegrationService,
    FleetbaseSettings,
)
from porterchain_fleetbase_adapter.auth import FleetbaseSsoClient
from porterchain_fleetbase_adapter.dispatch import DispatchService as DispatchSyncService
from porterchain_fleetbase_adapter.drivers import DriverService as DriverSyncService
from porterchain_fleetbase_adapter.events import (
    extract_fleetbase_order_id,
    extract_porterchain_order_id,
    resolve_domain_event,
    resolve_order_state,
)
from porterchain_fleetbase_adapter.orders import OrderService as OrderSyncService
from porterchain_fleetbase_adapter.routes import RouteService as RouteSyncService
from porterchain_fleetbase_adapter.tracking import TrackingService as TrackingSyncService
from porterchain_fleetbase_adapter.vehicles import VehicleService as VehicleSyncService
from porterchain_fleetbase_adapter.webhooks import parse_webhook_body, verify_signature

__all__ = [
    "DispatchSyncService",
    "DriverSyncService",
    "FleetbaseAdapter",
    "FleetbaseClient",
    "FleetbaseIntegrationService",
    "FleetbaseSettings",
    "FleetbaseSsoClient",
    "OrderSyncService",
    "RouteSyncService",
    "TrackingSyncService",
    "VehicleSyncService",
    "extract_fleetbase_order_id",
    "extract_porterchain_order_id",
    "parse_webhook_body",
    "resolve_domain_event",
    "resolve_order_state",
    "verify_signature",
]
