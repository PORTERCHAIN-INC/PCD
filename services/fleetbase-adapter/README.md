# Fleetbase Adapter


**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `porterchain-fleetbase-adapter`  
**Location:** `services/fleetbase-adapter/`  
**Role:** Sole HTTP integration boundary between Porterchain and Fleetbase.

---

## Architecture rule

All Fleetbase communication **must** go through this adapter. Porterchain apps (`apps/api`, worker, portals) must never call Fleetbase HTTP APIs directly.

**Orchestration layer:** `apps/api/src/porterchain_api/fleetbase_engine/` (sync, webhooks, retry queue).

---

## Modules

| Module | Class | Responsibility |
| ------ | ----- | -------------- |
| `client/` | `FleetbaseClient` | HTTP transport, auth, retries |
| `auth/` | `FleetbaseSsoClient` | SSO exchange (`/int/v1/porterchain/sso/*`) |
| `orders/` | `OrderService` | `POST/PUT /v1/orders` |
| `drivers/` | `DriverService` | Driver sync |
| `vehicles/` | `VehicleService` | Vehicle sync |
| `dispatch/` | `DispatchService` | Dispatch, schedule |
| `tracking/` | `TrackingService` | Tracker, ETA |
| `routes/` | `RouteService` | Route geometry, orchestrator |
| `webhooks/` | `WebhookService` | HMAC verify, parse |
| `events/` | `EventTranslator` | Fleetbase → Porterchain events |
| `pod/` | `PodService` | Proof of delivery |
| `integration.py` | `FleetbaseAdapter` | Facade |

---

## Usage

```python
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings

adapter = FleetbaseAdapter(FleetbaseSettings(
    api_url="http://localhost:8000",
    api_key="flb_live_...",
    company_uuid="...",
    dispatch_bridge=True,
))

fleetbase_order_id = adapter.sync_order({...})
```

Factory in API: `apps/api/src/porterchain_api/services/fleetbase_integration.py`

---

## Install

```bash
cd apps/api && pip install -e ../../services/fleetbase-adapter
```

---

## Documentation

| Document | Purpose |
| -------- | ------- |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](../../FLEETBASE_ADAPTER_ARCHITECTURE.md) | Full architecture |
| [EXTENSION_GUIDE.md](../../EXTENSION_GUIDE.md) | How to extend |
| [FLEETBASE_INTEGRATION.md](../../FLEETBASE_INTEGRATION.md) | End-to-end integration |
| [UPGRADE_GUIDE.md](../../UPGRADE_GUIDE.md) | Version upgrades |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../masterrule.md](../../masterrule.md) | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

