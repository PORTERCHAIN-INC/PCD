# Fleetbase Adapter

**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-08-07

**Package:** `porterchain-fleetbase-adapter`  
**Location:** `services/fleetbase-adapter/`  
**Role:** Sole HTTP integration boundary between Porterchain and Fleetbase.

---

## Compatibility matrix (runtime SSOT)

| Fleetbase package        | Supported runtime | Notes                                                                                          |
| ------------------------ | ----------------- | ---------------------------------------------------------------------------------------------- |
| `fleetbase/fleetops-api` | **0.6.59**        | Orchestrator `/v1/orchestrator/run\|commit`, ManifestController `/int/v1/fleet-ops/manifests*` |
| `fleetbase/core-api`     | **1.6.55**        | Bearer API + webhook surface used by this adapter                                              |

Pinned via `infrastructure/docker/fleetbase.porterchain.override.yml` (`fleetbase/fleetbase-api@sha256:24c0fbe5e465…`). Host `apps/fleetbase` v0.7.40 lock (0.6.48) is **not** the adapter contract target.

| Module                         | Class                                                   | Min fleetops               |
| ------------------------------ | ------------------------------------------------------- | -------------------------- |
| `routes/` orchestrator         | `RouteService.run_orchestrator` / `commit_orchestrator` | 0.6.48+ (verify on 0.6.59) |
| `manifests/`                   | `ManifestService`                                       | 0.6.48+ (list/show/cancel) |
| `orders/` multi-stop waypoints | `OrderService` + mappers                                | 0.6.59 runtime             |

---

## Architecture rule

All Fleetbase communication **must** go through this adapter. Porterchain apps (`apps/api`, worker, portals) must never call Fleetbase HTTP APIs directly.

**Orchestration layer:** `apps/api/src/porterchain_api/fleetbase_engine/` (sync, webhooks, retry queue).

---

## Modules

| Module           | Class                | Responsibility                             |
| ---------------- | -------------------- | ------------------------------------------ |
| `client/`        | `FleetbaseClient`    | HTTP transport, auth, retries              |
| `auth/`          | `FleetbaseSsoClient` | SSO exchange (`/int/v1/porterchain/sso/*`) |
| `orders/`        | `OrderService`       | `POST/PUT /v1/orders`                      |
| `drivers/`       | `DriverService`      | Driver sync                                |
| `vehicles/`      | `VehicleService`     | Vehicle sync                               |
| `dispatch/`      | `DispatchService`    | Dispatch, schedule                         |
| `tracking/`      | `TrackingService`    | Tracker, ETA                               |
| `routes/`        | `RouteService`       | Route geometry, orchestrator               |
| `manifests/`     | `ManifestService`    | Manifest list/show/cancel                  |
| `webhooks/`      | `WebhookService`     | HMAC verify, parse                         |
| `events/`        | `EventTranslator`    | Fleetbase → Porterchain events             |
| `pod/`           | `PodService`         | Proof of delivery                          |
| `integration.py` | `FleetbaseAdapter`   | Facade                                     |

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

| Document                                                                     | Purpose                |
| ---------------------------------------------------------------------------- | ---------------------- |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](../../FLEETBASE_ADAPTER_ARCHITECTURE.md) | Full architecture      |
| [CONTRIBUTING_GUIDE.md](../../CONTRIBUTING_GUIDE.md)                         | How to extend          |
| [FLEETBASE_INTEGRATION.md](../../FLEETBASE_INTEGRATION.md)                   | End-to-end integration |
| [UPGRADE_GUIDE.md](../../UPGRADE_GUIDE.md)                                   | Version upgrades       |

---
