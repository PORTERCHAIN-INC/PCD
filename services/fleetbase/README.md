# Fleetbase Integration Service

**Package:** `porterchain-fleetbase`  
**Location:** `services/fleetbase/`  
**Role:** Porterchain ↔ Fleetbase logistics engine bridge

## Architecture

```
Website / Merchant Portal / Admin
         ↓
   Porterchain API (:8001)
         ↓
  FleetbaseIntegrationService
         ↓
   Fleetbase API v1 (:8000)
```

**Rule:** Frontends never call Fleetbase directly. All logistics operations go through Porterchain API.

## Package structure

```
services/fleetbase/
├── pyproject.toml
└── porterchain_fleetbase/
    ├── client/          # HTTP client (Bearer flb_live_*)
    ├── orders/          # Order sync
    ├── drivers/         # Driver sync
    ├── vehicles/        # Vehicle sync
    ├── dispatch/        # Dispatch / schedule / start / complete
    ├── tracking/        # Tracker, ETA, proofs
    ├── routes/          # Route geometry, orchestrator
    ├── webhooks/        # Signature verify + parse
    ├── events/          # Fleetbase → Porterchain state map
    ├── integration.py   # Facade
    ├── mappers.py       # Address/order payload builders
    └── config.py        # FleetbaseSettings
```

## Sync operations

| Operation         | Trigger                                          | Fleetbase API                    |
| ----------------- | ------------------------------------------------ | -------------------------------- |
| **Order sync**    | `DISPATCH_READY`, booking confirm, merchant book | `POST /v1/orders`                |
| **Driver sync**   | Admin approves driver                            | `POST /v1/drivers`               |
| **Vehicle sync**  | Admin approves driver (active vehicle)           | `POST /v1/vehicles`              |
| **Dispatch sync** | Admin assigns driver                             | `PATCH /v1/orders/{id}/dispatch` |
| **Tracking sync** | `GET /v1/orders/{tracking}/tracking`             | `GET /v1/orders/{id}/tracker`    |
| **Status sync**   | `POST /webhooks/fleetbase`                       | Webhook events                   |
| **Proof sync**    | On `order.completed` webhook                     | `GET /v1/orders/{id}/proofs`     |

## Porterchain API wiring

| File                                                    | Role                                 |
| ------------------------------------------------------- | ------------------------------------ |
| `apps/api/.../services/fleetbase_integration.py`        | Settings factory                     |
| `apps/api/.../booking_engine/fleetbase_sync_service.py` | DB-aware sync orchestration          |
| `apps/api/.../routers/webhooks.py`                      | `POST /webhooks/fleetbase`           |
| `apps/api/.../routers/orders.py`                        | `GET /v1/orders/{tracking}/tracking` |

## Environment variables

| Variable                         | Required    | Description                             |
| -------------------------------- | ----------- | --------------------------------------- |
| `FLEETBASE_API_URL`              | Yes         | `http://localhost:8000`                 |
| `FLEETBASE_API_KEY`              | Yes         | `flb_live_*` from Fleetbase dev console |
| `FLEETBASE_DEFAULT_COMPANY_UUID` | Yes         | Company UUID from onboarding            |
| `FLEETBASE_DISPATCH_BRIDGE`      | Yes         | `true` to enable sync                   |
| `FLEETBASE_WEBHOOK_SECRET`       | Recommended | API credential secret for webhook HMAC  |

## Fleetbase webhook setup

1. Open Fleetbase console → Developer → Webhooks
2. URL: `http://localhost:8001/webhooks/fleetbase` (or production API URL)
3. Subscribe: `order.dispatched`, `order.driver_assigned`, `order.completed`, `order.canceled`
4. Use same API credential secret as `FLEETBASE_WEBHOOK_SECRET`

## Install

```bash
cd apps/api && pip install -e ../../services/fleetbase
```

Or via `apps/api/requirements.txt` (editable install).

## Related docs

- [FLEETBASE_INTEGRATION.md](../../FLEETBASE_INTEGRATION.md) — full integration guide
- [FLEETBASE_ANALYSIS.md](../../FLEETBASE_ANALYSIS.md) — module ownership
- [FLEETBASE_APIS.md](../../FLEETBASE_APIS.md) — Fleetbase route reference
