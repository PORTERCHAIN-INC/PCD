# Porterchain Platform Foundation

**Status:** Infrastructure scaffolding — no feature or UI changes  
**Date:** June 29, 2026

This document describes the modular enterprise foundation added to the Porterchain monorepo. All customer-facing surfaces (website booking widget, auth UX, merchant pages, driver UI) remain unchanged.

---

## Architecture layers

```
┌─────────────────────────────────────────────────────────────────┐
│  apps/          Client applications (website, api, worker, …)   │
├─────────────────────────────────────────────────────────────────┤
│  packages/      TypeScript shared libs (types, auth, events)    │
├─────────────────────────────────────────────────────────────────┤
│  services/      Internal Python service layer                   │
├─────────────────────────────────────────────────────────────────┤
│  shared/        Cross-cutting hooks, providers, Python shared   │
├─────────────────────────────────────────────────────────────────┤
│  infrastructure/   Docker, CI, scripts                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Directory map

| Path                                    | Responsibility                                     |
| --------------------------------------- | -------------------------------------------------- |
| `apps/website/`                         | Public site (unchanged UX)                         |
| `apps/api/`                             | Porterchain FastAPI — customer-facing API          |
| `apps/worker/`                          | Async queue processor                              |
| `packages/types/`                       | `@porterchain/types` — roles, events, ownership    |
| `packages/auth/`                        | `@porterchain/auth` — RBAC, Clerk metadata mapping |
| `packages/events/`                      | `@porterchain/events` — domain event catalog       |
| `packages/queue/`                       | `@porterchain/queue` — queue names and messages    |
| `packages/config/`                      | `@porterchain/config` — ESLint, Prettier, TS base  |
| `shared/python/porterchain_shared/`     | Python auth, events, queues, config                |
| `services/python/porterchain_services/` | Fleetbase, Stripe, Maps, Notifications, …          |
| `services/fleetbase/`                   | Fleetbase deployment config (engine only)          |

---

## Authentication (Clerk only)

| Role            | Purpose                                         |
| --------------- | ----------------------------------------------- |
| `visitor`       | Anonymous quote                                 |
| `customer`      | Retail dashboard                                |
| `merchant`      | B2B portal                                      |
| `driver`        | Mobile execution (Porterchain JWT for sessions) |
| `dispatcher`    | Dispatch operations                             |
| `support`       | Tickets, exceptions                             |
| `sales`         | CRM, leads                                      |
| `fleet_manager` | Fleet utilization                               |
| `admin`         | Operations                                      |
| `super_admin`   | Full system                                     |

- **RBAC:** Multiple roles per user via Clerk public metadata
- **JWT:** Clerk JWKS verification on API; refresh tokens for driver API (stub)
- **Implementation:** `shared/python/porterchain_shared/auth/`, `packages/auth/`

---

## Database ownership

| Owner                        | Data                                                                                                     |
| ---------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Porterchain (PostgreSQL)** | Users, merchants, visitors, quotes, contracts, pricing, invoices, billing, CRM, notifications, analytics |
| **Fleetbase (MySQL)**        | Vehicles, drivers, orders, dispatch, routes, GPS, waypoints, tracking, POD                               |

Merchants and customers **never** authenticate against Fleetbase directly.

---

## Internal services

| Service       | Module                               | Notes                                         |
| ------------- | ------------------------------------ | --------------------------------------------- |
| API Gateway   | `porterchain_services.gateway`       | Service registry, `/internal/services` health |
| Fleetbase     | `porterchain_services.fleetbase`     | All Fleetbase HTTP via Porterchain API        |
| Stripe        | `porterchain_services.stripe`        | Checkout + webhooks                           |
| Maps          | `porterchain_services.maps`          | Valhalla / OSRM routing                       |
| Notifications | `porterchain_services.notifications` | Email, SMS, push queues                       |
| Pricing       | `porterchain_services.pricing`       | Calculator protocol (API registers impl)      |
| Merchant      | `porterchain_services.merchant`      | B2B lifecycle events                          |
| Driver        | `porterchain_services.driver`        | Execution boundary                            |
| Dispatch      | `porterchain_services.dispatch`      | Assignment queue                              |
| Customer      | `porterchain_services.customer`      | Retail lifecycle                              |
| Visitor       | `porterchain_services.visitor`       | Anonymous session, leads, abandoned checkout  |

---

## Event system

Immutable domain events with envelope schema per `EVENT_FLOW.md`.

- **Catalog:** `porterchain_shared.events.catalog.DomainEventType`
- **Publisher:** Redis Streams (production) or in-memory (local)
- **Bridge:** `emit_domain_event()` in API also publishes to event bus

Examples: `quote.created`, `payment.succeeded`, `order.booked`, `fleetbase.order_created`, `visitor.session_merged`

---

## Queue system

| Queue      | Worker consumer            |
| ---------- | -------------------------- |
| `emails`   | SMTP delivery              |
| `sms`      | Twilio                     |
| `push`     | Firebase                   |
| `dispatch` | Fleetbase sync             |
| `billing`  | Stripe reconciliation      |
| `reports`  | Report generation          |
| `webhooks` | Merchant outbound webhooks |

Run worker: `pnpm dev:worker`

---

## Local development

```bash
# Infrastructure
pnpm docker:up          # MySQL, Redis, PostgreSQL, Mailhog

# API
cd apps/api && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
pnpm dev:api            # port 8001

# Worker
pnpm dev:worker

# Website (unchanged)
pnpm --filter @porterchain/website dev
```

### Health endpoints

| Endpoint                 | Purpose                 |
| ------------------------ | ----------------------- |
| `GET /health`            | API liveness            |
| `GET /internal/health`   | Gateway liveness        |
| `GET /internal/services` | Service registry status |

---

## What was NOT changed

- Website booking widget UI and flow
- Authentication UX on continue booking page
- Merchant or driver application surfaces
- Existing API route contracts (`/v1/quotes`, `/v1/bookings`, etc.)

---

## Related documents

- [SYSTEM_ARCHITECTURE.md](./SYSTEM_ARCHITECTURE.md)
- [FOLDER_STRUCTURE.md](./FOLDER_STRUCTURE.md)
- [EVENT_FLOW.md](./EVENT_FLOW.md)
- [ROLE_PERMISSIONS.md](./ROLE_PERMISSIONS.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
