# Application Flow

> **Source:** `apps/api/src/porterchain_api/routers/`, `main.py`, `platform/bus.py`

## Request Path

Every frontend application communicates exclusively with the Porterchain API at `NEXT_PUBLIC_PORTERCHAIN_API_URL` (default `http://localhost:8001`). No frontend performs direct Fleetbase HTTP calls.

```
Website / Customer / Merchant / Admin / Driver
        ↓  HTTPS /v1/*  (Driver: /driver-api/v1 via Next proxy)
FastAPI Router (Controller)
        ↓
Application Service (*_engine/*_service.py)
        ↓
Repository → Database
        ↓ (async side effects)
Event Bus → Worker → Queues
        ↓ (logistics execution)
fleetbase_engine → fleetbase-adapter → Fleetbase
```

## Router → Service Mapping

| Router prefix                                                    | Auth                     | Primary engines                                      |
| ---------------------------------------------------------------- | ------------------------ | ---------------------------------------------------- |
| `/v1/quotes`, `/v1/booking-drafts`, `/v1/orders`, `/v1/payments` | Clerk (optional/public)  | `booking_engine`                                     |
| `/v1/customers`                                                  | Clerk                    | `booking_engine.CustomerService`                     |
| `/v1/merchant`                                                   | Clerk + merchant context | `merchant_engine`                                    |
| `/v1/admin`                                                      | Clerk + admin RBAC       | `admin_engine`                                       |
| `/v1/admin/operations`                                           | Admin RBAC               | `admin_engine.ControlTowerService`, `LiveMapService` |
| `/v1/admin/crm`, `/merchants`, `/drivers`                        | Admin RBAC               | `admin_engine`, `CrmSalesService`                    |
| `/driver-api/v1`                                                 | Porterchain JWT          | `driver_engine`, `porterchain_driver`                |
| `/webhooks`                                                      | Signature verify         | `StripeWebhookService`, `WebhookIngressService`      |

## Middleware

1. `CORSMiddleware` — origins from `settings.cors_origin_list`
2. `RequestIdMiddleware` — `X-Request-ID` propagation (`platform/middleware.py`)

## Diagram

```mermaid
sequenceDiagram
  participant UI as Next.js UI
  participant Router as FastAPI Router
  participant Auth as auth/clerk.py
  participant Svc as Application Service
  participant Repo as SQLAlchemy / Repository
  participant DB as Database
  participant Bus as Event Bus
  participant Worker as apps/worker
  participant FBE as fleetbase_engine
  participant FBA as fleetbase-adapter
  participant FB as Fleetbase API

  UI->>Router: HTTPS /v1/*
  Router->>Auth: get_clerk_user_id / get_admin_context / get_merchant_context
  Auth-->>Router: principal
  Router->>Svc: single service method
  Svc->>Repo: CRUD / queries
  Repo->>DB: SQL
  DB-->>Repo: entities
  Repo-->>Svc: entities
  Svc->>Bus: emit_event (side effects)
  Bus->>Worker: async handlers / queues
  alt dispatch ready
    Worker->>FBE: sync_order_from_event
    FBE->>FBA: FleetbaseIntegrationBridge
    FBA->>FB: HTTP
    FB-->>FBA: response
  end
  Svc-->>Router: DTO / result
  Router-->>UI: JSON response
```

## PlantUML

See [plantuml/application_flow.puml](./plantuml/application_flow.puml)
