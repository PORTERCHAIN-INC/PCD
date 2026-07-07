# Porterchain ↔ Fleetbase Integration

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Version:** 2.0  
**Status:** Implemented

> **Adapter detail:** [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) · **Topology:** [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)

---

## Overview

Fleetbase is Porterchain's **internal logistics engine**. Porterchain owns customer experience, auth (Clerk), pricing, billing, and CRM. Fleetbase owns dispatch, GPS tracking, routes, and proof of delivery execution.

```
┌─────────────┐     ┌─────────────────┐     ┌──────────────────────┐     ┌─────────────┐
│  Frontends  │────►│ Porterchain API │────►│ fleetbase_engine +   │────►│ Fleetbase   │
│  :3000–3004 │     │  :8001          │     │ fleetbase-adapter    │     │ API :8000   │
│  mobile ×2  │     │  /v1/*          │     │                      │     └─────────────┘
└─────────────┘     │  /webhooks/*    │     └──────────────────────┘
                    └────────▲────────┘
                             │ Event bus (order.dispatch_ready, webhooks)
                    Admin SSO → Fleetbase Console :4200 (ops only)
```

**Never:** Frontend → Fleetbase API  
**Always:** Frontend → Porterchain API → `fleetbase_engine` → `services/fleetbase-adapter/` → Fleetbase

---

## Ownership matrix

| Domain                                        | Owner       |
| --------------------------------------------- | ----------- |
| Authentication (Clerk)                        | Porterchain |
| Website, merchant, admin, customer, driver UX | Porterchain |
| Pricing, billing, CRM, commercial order state | Porterchain |
| Drivers, vehicles, ops orders, dispatch       | Fleetbase   |
| GPS tracking, routes, POD capture             | Fleetbase   |

---

## Integration layers

| Layer          | Path                                       | Role                                               |
| -------------- | ------------------------------------------ | -------------------------------------------------- |
| Adapter (HTTP) | `services/fleetbase-adapter/`              | Sole Fleetbase HTTP boundary                       |
| Sync engine    | `apps/api/.../fleetbase_engine/`           | BookingSyncService, WebhookProcessor, translators  |
| Event handlers | `booking_engine/fleetbase_sync_handler.py` | React to `order.dispatch_ready`, webhooks          |
| Factory        | `services/fleetbase_integration.py`        | `get_fleetbase_integration()` → `FleetbaseAdapter` |

**Production order sync:** `POST /v1/orders` via adapter (API key).  
**SSO extension routes:** `POST /int/v1/porterchain/sso/*` — requires Fleetbase `porterchain-bridge` extension (see [SSO.md](./SSO.md)).

---

## Sync flows (event-driven)

| Trigger                | Path                                                                      |
| ---------------------- | ------------------------------------------------------------------------- |
| `order.dispatch_ready` | Event bus → `sync_order_from_event` → `BookingSyncService` → adapter      |
| Admin approves driver  | `AdminDriverService` → sync driver + vehicle                              |
| Admin assigns driver   | `AdminOperationsService` → sync dispatch                                  |
| Customer tracking      | `GET /v1/orders/{tracking}/tracking` → adapter tracker API                |
| Fleetbase webhook      | `POST /webhooks/fleetbase` → `WebhookIngressService` → `WebhookProcessor` |

Order sync is **never** called directly from booking/admin services at call sites — handlers only (masterrule §12).

---

## FleetExecutor (Phase 2 hook — ADR-010)

Mixed-fleet delivery (human driver today; autonomous vehicle, drone, robot later) uses an **anti-corruption layer** behind the Fleetbase adapter — not new Porterchain deployables.

```python
# Conceptual port (implementations live in services/fleetbase-adapter/ or future adapters)
class FleetExecutor(Protocol):
    executor_type: str  # human_driver | autonomous_vehicle | drone | robot

    def dispatch(self, order_id: str, payload: dict) -> str: ...
    def tracking_snapshot(self, external_id: str) -> dict: ...
    def cancel(self, external_id: str) -> None: ...
```

| Field           | Location                                                | Default                     |
| --------------- | ------------------------------------------------------- | --------------------------- |
| `executor_type` | `booking_engine/order_metadata.resolve_executor_type()` | `human_driver`              |
| External ID     | `orders.fleetbase_order_id`                             | Fleetbase human fleet today |

New executor types plug in as **adapter strategies**; Porterchain order state and billing stay unchanged.

---

## Porterchain API endpoints

| Method | Path                                    | Description                       |
| ------ | --------------------------------------- | --------------------------------- |
| GET    | `/v1/orders/{tracking_number}`          | Order summary (Porterchain DB)    |
| GET    | `/v1/orders/{tracking_number}/tracking` | Order + live Fleetbase tracking   |
| POST   | `/webhooks/fleetbase`                   | Inbound Fleetbase status webhooks |
| POST   | `/v1/auth/sso/fleetbase`                | Issue SSO token for ops console   |

Merchant and admin endpoints trigger sync internally — no Fleetbase URLs exposed to clients.

---

## Configuration

```env
FLEETBASE_API_URL=http://localhost:8000
FLEETBASE_API_KEY=flb_live_...
FLEETBASE_DEFAULT_COMPANY_UUID=...
FLEETBASE_DISPATCH_BRIDGE=true
FLEETBASE_WEBHOOK_SECRET=...
PORTERCHAIN_DISPATCHER_API_KEY=...
```

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) and `env/fleetbase.env.example`.

---

## Development setup

```bash
pnpm docker:fleetbase:up    # Fleetbase stack :8000 / :4200
pnpm docker:up              # PostgreSQL + Redis for Porterchain
pnpm dev:api                # Porterchain API :8001
pnpm dev:worker             # Event bus consumer
```

Complete Fleetbase onboarding at http://localhost:4200 and copy company UUID.

---

## Fleetbase UI policy

- **Do not modify** upstream Fleetbase vendor code (`apps/fleetbase/**`)
- Ops staff use Fleetbase console (:4200) via SSO or direct login
- Merchants and customers use Porterchain portals only

---

## Error handling

| Scenario                  | Behavior                                                          |
| ------------------------- | ----------------------------------------------------------------- |
| Bridge disabled           | Sync skipped, logged                                              |
| Fleetbase unreachable     | Order stays in Porterchain; retry queue / `fleetbase.sync_failed` |
| Invalid webhook signature | Rejected (logged)                                                 |
| Invalid state transition  | Logged, no crash                                                  |

---

## Related documents

| Document                                                                 | Purpose                             |
| ------------------------------------------------------------------------ | ----------------------------------- |
| [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) | Adapter package structure           |
| [FLEETBASE_MODULES.md](./FLEETBASE_MODULES.md)                           | Per-module Porterchain decisions    |
| [EVENT_CATALOG.md](./EVENT_CATALOG.md)                                   | Fleetbase-related domain events     |
| [DATABASE_OWNERSHIP_MATRIX.md](./DATABASE_OWNERSHIP_MATRIX.md)           | Fleetbase/Porterchain data boundary |
| [INTEGRATIONS.md](./INTEGRATIONS.md)                                     | All external integrations           |
| [docs/archive/README.md](./docs/archive/README.md#fleetbase-detail)      | Historical Fleetbase detail reports |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
