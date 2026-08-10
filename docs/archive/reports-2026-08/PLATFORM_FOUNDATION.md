# Porterchain Platform Foundation

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Status:** Implemented — modular enterprise foundation

This document describes the modular enterprise foundation of the Porterchain monorepo: the layered architecture, shared packages, internal services, event bus, and queues that all customer-facing surfaces build on.

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

| Path                                                   | Responsibility                                     |
| ------------------------------------------------------ | -------------------------------------------------- |
| `website/`                                             | Public site + booking (:3000)                      |
| `apps/api/`                                            | Porterchain FastAPI — all business logic (:8001)   |
| `apps/worker/`                                         | Async queue + event consumer                       |
| `apps/{admin,merchant-portal,customer,driver-portal}/` | Next.js portals                                    |
| `apps/{mobile-driver,mobile-customer}/`                | Expo mobile apps                                   |
| `packages/types/`                                      | `@porterchain/types` — roles, events, ownership    |
| `packages/auth/`                                       | `@porterchain/auth` — RBAC, Clerk metadata mapping |
| `packages/events/`                                     | `@porterchain/events` — domain event catalog       |
| `packages/queue/`                                      | `@porterchain/queue` — queue names and messages    |
| `packages/config/`                                     | `@porterchain/config` — ESLint, Prettier, TS base  |
| `shared/python/porterchain_shared/`                    | Python auth, events, queues, config                |
| `services/python/porterchain_services/`                | Stripe, Maps, Notifications, …                     |
| `services/fleetbase-adapter/`                          | Sole Fleetbase integration boundary                |

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
| Fleetbase     | `porterchain_fleetbase_adapter`      | All Fleetbase HTTP via the adapter boundary   |
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

Immutable domain events with envelope schema per `EVENT_BUS.md`.

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

# Frontends
pnpm dev:website        # :3000
pnpm dev:merchant       # :3001
pnpm dev:admin          # :3002
pnpm dev:driver         # :3003
pnpm dev:customer       # :3004
```

### Health endpoints

| Endpoint                 | Purpose                 |
| ------------------------ | ----------------------- |
| `GET /health`            | API liveness            |
| `GET /internal/health`   | Gateway liveness        |
| `GET /internal/services` | Service registry status |

---

## Related documents

- [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md)
- [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)
- [EVENT_BUS.md](./EVENT_BUS.md)
- [ROLE_PERMISSIONS.md](./ROLE_PERMISSIONS.md)
- [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
