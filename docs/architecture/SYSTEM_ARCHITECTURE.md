# System Architecture

**Type:** CANONICAL
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05  
**Reference:** [masterrule.md](../../masterrule.md) §21

## Overview

Porterchain is a logistics orchestration platform. All commercial logic lives in the **Porterchain API** (`apps/api`, port **8001**). **Fleetbase** (`:8000`) is the execution engine for dispatch, GPS, routes, and POD. Frontends never call Fleetbase HTTP directly.

## Components

| Layer             | Path                                    | Port | Role                                                    |
| ----------------- | --------------------------------------- | ---- | ------------------------------------------------------- |
| Website           | `website/`                              | 3000 | Marketing + guest track; CTAs → customer portal `:3004` |
| Merchant Portal   | `apps/merchant-portal/`                 | 3001 | B2B bookings, bulk, billing, API keys                   |
| Admin Portal      | `apps/admin/`                           | 3002 | Ops control tower — dispatch, orders, finance (not CRM) |
| Driver Portal     | `apps/driver-portal/`                   | 3003 | Driver web UI (proxied to `/driver-api/v1`)             |
| Customer Portal   | `apps/customer/`                        | 3004 | Retail quote/book/pay, dashboard, support, rebook       |
| Mobile Driver     | `apps/mobile-driver/`                   | —    | Expo app → `/driver-api/v1/*`                           |
| Mobile Customer   | `apps/mobile-customer/`                 | —    | Expo app → `/v1/*`                                      |
| Porterchain API   | `apps/api/`                             | 8001 | FastAPI orchestrator, all `*_engine` services           |
| Worker            | `apps/worker/`                          | —    | Redis event bus + queue consumer                        |
| Fleetbase Adapter | `services/fleetbase-adapter/`           | —    | Sole Fleetbase HTTP boundary                            |
| Event Bus         | `services/event-bus/`                   | —    | `porterchain_event_bus` + handler registry              |
| Pricing Engine    | `services/pricing-engine/`              | —    | `porterchain_pricing` library                           |
| Shared Services   | `services/python/porterchain_services/` | —    | Stripe, maps, notifications                             |
| Shared Python     | `shared/python/porterchain_shared/`     | —    | Config, events catalog, queue names                     |

## Data Stores

| Store         | Usage                                            |
| ------------- | ------------------------------------------------ |
| PostgreSQL 18 | Primary domain DB (`porterchain_api/models*.py`) |
| Redis         | Event bus transport, task queues, idempotency    |
| Fleetbase DB  | Operational drivers, dispatch, GPS (external)    |

## Diagram

```mermaid
flowchart TB
  subgraph Frontends["Frontends (Next.js)"]
    WEB["Website :3000"]
    CUST["Customer Portal :3004"]
    MERCH["Merchant Portal :3001"]
    ADMIN["Admin Portal :3002"]
    DRIVER["Driver Portal :3003"]
    MOBILE_D["Mobile Driver (Expo)"]
    MOBILE_C["Mobile Customer (Expo)"]
  end

  subgraph API["Porterchain API (FastAPI :8001)"]
  direction TB
    ROUTERS["Routers / Controllers"]
    BE["booking_engine"]
    ME["merchant_engine"]
    AE["admin_engine"]
    FE["fleetbase_engine"]
    DE["driver_engine"]
    PE["pricing_engine"]
    BLE["billing_engine"]
    NE["notification_engine"]
    ROUTERS --> BE & ME & AE & FE & DE & PE & BLE & NE
  end

  subgraph Data["Data & Messaging"]
    PG[("PostgreSQL 18")]
    REDIS[("Redis")]
    EB["Event Bus<br/>porterchain_event_bus"]
    Q["Queues<br/>emails|sms|push|billing|webhooks|dispatch|reports"]
  end

  subgraph Worker["apps/worker"]
    WP["Queue + Event Consumers"]
  end

  subgraph Adapters["Integration Adapters"]
    FBA["fleetbase-adapter<br/>porterchain_fleetbase_adapter"]
    STRIPE["Stripe SDK<br/>services/stripe_service"]
    MAPS["MapsService<br/>OSRM / Valhalla"]
    GMAPS["@porterchain/maps<br/>Google Maps (viz)"]
  end

  subgraph External["External Systems"]
    FB["Fleetbase :8000"]
    CLERK["Clerk Auth"]
    STRIPE_EXT["Stripe"]
    OSRM["OSRM"]
    VAL["Valhalla :8002"]
    GAPI["Google Maps API"]
    FIREBASE["Firebase (push)"]
  end

  WEB & CUST & MERCH & ADMIN & DRIVER & MOBILE_D & MOBILE_C -->|"HTTPS /v1/*"| ROUTERS
  ADMIN -->|"WS /v1/notifications/ws"| ROUTERS
  BE & ME & AE & FE & DE --> PG
  BE & ME & AE --> EB
  EB --> REDIS
  EB --> WP
  WP --> Q
  Q --> WP
  WP --> NE & BLE
  FE & DE --> FBA
  FBA --> FB
  BE --> STRIPE
  STRIPE --> STRIPE_EXT
  BE & PE --> MAPS
  MAPS --> OSRM & VAL
  WEB & MERCH & ADMIN --> GMAPS
  GMAPS --> GAPI
  WEB & CUST & MERCH & ADMIN & DRIVER --> CLERK
  NE --> FIREBASE
```

## Source Files

- App entry: `apps/api/src/porterchain_api/main.py`
- Settings: `shared/python/porterchain_shared/config/settings.py`
- Integrations: `integrations.yaml`, `INTEGRATIONS.md`

## PlantUML

See [plantuml/system_architecture.puml](./plantuml/system_architecture.puml)
---
