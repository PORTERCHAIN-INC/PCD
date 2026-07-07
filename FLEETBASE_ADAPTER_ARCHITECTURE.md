# Fleetbase Adapter Architecture

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `porterchain-fleetbase-adapter` at `services/fleetbase-adapter/`  
**Status:** Active — sole Porterchain ↔ Fleetbase HTTP boundary

---

## Purpose

The Fleetbase adapter isolates Porterchain from Fleetbase API details. Porterchain owns customer experience, pricing, billing, and CRM. Fleetbase owns fleet operations, routing, GPS, and execution mechanics.

**Rule:** No Porterchain application may call Fleetbase HTTP APIs directly. All communication flows through `services/fleetbase-adapter/`.

---

## Position in the stack

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Website    │  │   Merchant   │  │    Admin     │  │  Customer    │
│   :3000      │  │   :3001      │  │    :3002     │  │  :3004       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
                ┌────────▼────────┐
                │  Porterchain API │
                │     :8001        │
                └────────┬────────┘
                         │
                ┌────────▼────────────────────────┐
                │  services/fleetbase-adapter/     │
                │  FleetbaseAdapter (facade)       │
                └────────┬────────────────────────┘
                         │ HTTPS + API key
                ┌────────▼────────┐
                │  Fleetbase API   │
                │     :8000        │
                │  (apps/fleetbase)│
                └─────────────────┘
```

Fleetbase source remains at `apps/fleetbase/` (upstream). The logical vendor reference is `vendor/fleetbase/README.md`.

---

## Package structure

```
services/fleetbase-adapter/
└── porterchain_fleetbase_adapter/
    ├── client/          FleetbaseClient — HTTP transport
    ├── auth/            FleetbaseSsoClient — SSO exchange
    ├── orders/          OrderService
    ├── drivers/         DriverService
    ├── vehicles/        VehicleService
    ├── dispatch/        DispatchService
    ├── tracking/        TrackingService
    ├── routes/          RouteService
    ├── webhooks/        WebhookService
    ├── events/          EventTranslator
    ├── pod/             PodService
    ├── mappers.py       Porterchain → Fleetbase payloads
    ├── errors.py        ErrorHandler
    ├── retry.py         RetryPolicy
    ├── config.py        FleetbaseSettings
    ├── exceptions.py    Typed errors
    └── integration.py   FleetbaseAdapter facade
```

---

## Component responsibilities

### FleetbaseClient

- Builds authenticated HTTP requests (`Authorization: Bearer flb_live_*`)
- Sends `X-Fleetbase-Version` header for compatibility checks
- Applies `RetryPolicy` on transient failures (408, 429, 5xx)
- Raises `FleetbaseApiError` with status code and body snippet
- Raises `FleetbaseNotConfiguredError` when bridge is disabled

### Domain services

| Service           | Fleetbase endpoints                     | Porterchain use                      |
| ----------------- | --------------------------------------- | ------------------------------------ |
| `OrderService`    | `POST/PUT /v1/orders`                   | Sync commercial orders after payment |
| `DriverService`   | `POST/PUT /v1/drivers`                  | Sync vetted driver partners          |
| `VehicleService`  | `POST/PUT /v1/vehicles`                 | Sync fleet vehicles                  |
| `DispatchService` | `PATCH /v1/orders/{id}/dispatch`        | Trigger dispatch, assign driver      |
| `TrackingService` | `GET /v1/orders/{id}/tracker`, `/eta`   | Public tracking API                  |
| `RouteService`    | `/distance-and-time`, `/orchestrator/*` | Route geometry, batch optimization   |
| `PodService`      | `GET /v1/orders/{id}/proofs`            | Proof of delivery artifacts          |

### WebhookService

- Validates HMAC-SHA256 signatures (`sha256=` prefix)
- Parses Fleetbase webhook envelope
- Delegates event mapping to `EventTranslator`
- Returns normalized Porterchain update payload

### EventTranslator

Maps Fleetbase webhook events to Porterchain order states:

| Fleetbase event    | Porterchain state |
| ------------------ | ----------------- |
| `order.dispatched` | `DRIVER_ASSIGNED` |
| `order.started`    | `PICKED_UP`       |
| `order.completed`  | `DELIVERED`       |
| `order.canceled`   | `CANCELLED`       |
| `order.failed`     | `FAILED`          |

### ErrorHandler

- Centralizes logging for suppressed failures (sync operations return `None` rather than raising)
- Classifies configuration vs API vs retryable errors
- Produces structured error dicts for worker retry queues

### RetryPolicy

- Exponential backoff: `backoff * 2^(attempt-1)`
- Configurable via `FleetbaseSettings.max_retries` and `retry_backoff_seconds`
- Retries only idempotent-safe GET and transient POST failures

---

## FleetbaseAdapter facade

`FleetbaseAdapter` is the single entry point used by `apps/api`:

```python
from porterchain_fleetbase_adapter import FleetbaseAdapter, FleetbaseSettings

adapter = FleetbaseAdapter(FleetbaseSettings(
    api_url=settings.fleetbase_api_url,
    api_key=settings.fleetbase_api_key,
    company_uuid=settings.fleetbase_default_company_uuid,
    dispatch_bridge=settings.fleetbase_dispatch_bridge,
    webhook_secret=settings.fleetbase_webhook_secret,
))

fleetbase_order_id = adapter.sync_order(order_dict)
update = adapter.process_webhook(raw_bytes, json_body, signature=sig)
```

`FleetbaseIntegrationService` is a backward-compatible alias.

---

## Data mapping

Porterchain order fields map to Fleetbase via `mappers.py`:

- `pickup` / `dropoff` → Fleetbase `place` objects with GeoJSON Point
- `meta.porterchain_order_id` → round-trip correlation for webhooks
- `internal_id` → tracking number / order number for ops search

**Never** store Porterchain pricing, Stripe IDs, or merchant contract terms in Fleetbase payloads.

---

## Authentication

| Flow             | Mechanism                                                                    |
| ---------------- | ---------------------------------------------------------------------------- |
| Server-to-server | Fleetbase API key (`flb_live_*`) in adapter client                           |
| Ops console SSO  | `FleetbaseSsoClient` → `/int/v1/porterchain/sso/exchange` (bridge extension) |
| Webhooks inbound | HMAC signature verified by `WebhookService`                                  |

Porterchain users never authenticate directly against Fleetbase. Clerk is the IdP.

---

## Configuration

| Setting           | Env variable                     | Default                 |
| ----------------- | -------------------------------- | ----------------------- |
| `api_url`         | `FLEETBASE_API_URL`              | `http://localhost:8000` |
| `api_key`         | `FLEETBASE_API_KEY`              | —                       |
| `company_uuid`    | `FLEETBASE_DEFAULT_COMPANY_UUID` | —                       |
| `dispatch_bridge` | `FLEETBASE_DISPATCH_BRIDGE`      | `true`                  |
| `webhook_secret`  | `FLEETBASE_WEBHOOK_SECRET`       | —                       |
| `max_retries`     | —                                | `3`                     |

Factory: `apps/api/src/porterchain_api/services/fleetbase_integration.py`

---

## API wiring

| Porterchain module                         | Adapter method                                     |
| ------------------------------------------ | -------------------------------------------------- |
| `fleetbase_engine/booking_sync_service.py` | `sync_order`, `sync_driver`, `sync_dispatch`       |
| `fleetbase_engine/webhook_processor.py`    | `process_webhook`                                  |
| `routers/webhooks.py`                      | `POST /webhooks/fleetbase`                         |
| `routers/orders.py`                        | `fetch_tracking`                                   |
| `auth/sso_service.py`                      | `FleetbaseSsoClient` → `/int/v1/porterchain/sso/*` |
| `driver_engine/` (DriverFleetbaseBridge)   | GPS, POD, route execution                          |

---

## Version compatibility

`FleetbaseClient` sends `X-Fleetbase-Version: v1` and logs warnings when the server responds with a different version header. Breaking Fleetbase upgrades require adapter mapper updates — see [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md).

---

## What does NOT belong in the adapter

| Concern                  | Correct location                                |
| ------------------------ | ----------------------------------------------- |
| Order pricing / Stripe   | `apps/api/booking_engine/`                      |
| Merchant CRM / contracts | `apps/api/` merchant domains                    |
| Clerk auth / RBAC        | `apps/api/auth/`                                |
| Public tracking UI       | `website/`                                      |
| Fleetbase console UI     | `apps/fleetbase/console/` (upstream, read-only) |

---

## Deprecated paths

Legacy `services/fleetbase/porterchain_fleetbase/` shim removed — use `porterchain_fleetbase_adapter` only.

---

## Related documents

| Document                                                                               | Purpose                                   |
| -------------------------------------------------------------------------------------- | ----------------------------------------- |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                                 | Integration overview                      |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                                 | Fleetbase route and integration reference |
| [UPGRADE_GUIDE.md](./UPGRADE_GUIDE.md)                                                 | Version upgrades                          |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) | Platform topology                         |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
