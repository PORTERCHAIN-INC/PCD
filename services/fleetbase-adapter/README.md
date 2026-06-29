# Fleetbase Adapter

**Package:** `porterchain-fleetbase-adapter`  
**Location:** `services/fleetbase-adapter/`  
**Role:** Sole integration boundary between Porterchain and Fleetbase.

## Architecture rule

All Fleetbase communication **must** go through this adapter. Porterchain apps (`apps/api`, worker, portals) must never call Fleetbase HTTP APIs directly.

## Modules

| Module | Class | Responsibility |
|--------|-------|----------------|
| `client/` | `FleetbaseClient` | HTTP transport, auth headers, retries |
| `auth/` | `FleetbaseSsoClient` | SSO token exchange, permission sync |
| `orders/` | `OrderService` | Order create/update/cancel |
| `drivers/` | `DriverService` | Driver sync |
| `vehicles/` | `VehicleService` | Vehicle sync |
| `dispatch/` | `DispatchService` | Dispatch, schedule, start, complete |
| `tracking/` | `TrackingService` | Tracker, ETA snapshots |
| `routes/` | `RouteService` | Route geometry, orchestrator |
| `webhooks/` | `WebhookService` | Signature validation, event parsing |
| `events/` | `EventTranslator` | Fleetbase event → Porterchain state |
| `pod/` | `PodService` | Proof of delivery fetch/normalize |
| `errors.py` | `ErrorHandler` | Structured error logging |
| `retry.py` | `RetryPolicy` | Transient failure retries |
| `integration.py` | `FleetbaseAdapter` | Facade for Porterchain API |

## Usage

```python
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings

adapter = FleetbaseAdapter(FleetbaseSettings(
    api_url="http://localhost:8000",
    api_key="flb_live_...",
    company_uuid="...",
))

fleetbase_order_id = adapter.sync_order({...})
```

## Install

```bash
cd apps/api && pip install -e ../../services/fleetbase-adapter
```

## Deprecated shim

`services/fleetbase/porterchain_fleetbase/` re-exports this package for backward compatibility. New code should import `porterchain_fleetbase_adapter` directly.

## Documentation

- [FLEETBASE_ADAPTER_ARCHITECTURE.md](../../FLEETBASE_ADAPTER_ARCHITECTURE.md)
- [EXTENSION_GUIDE.md](../../EXTENSION_GUIDE.md)
- [UPGRADE_GUIDE.md](../../UPGRADE_GUIDE.md)
