# Porterchain — Master Architecture Rules

**Type:** CANONICAL
**masterrule:** this document (§21)
**Last verified:** 2026-07-05

**Version:** 3.3  
**Status:** APPROVED  
**Owner:** Ravi Chauhan  
**Last updated:** July 5, 2026

> This document is the **single source of truth** for Porterchain. Every Cursor prompt, feature, refactor, review, and integration must follow it.  
> For implementation status vs this diagram, see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md).

---

## Table of contents

1. [Locked architecture](#1-locked-architecture)
2. [Core principles](#2-core-principles)
3. [Layered architecture (mandatory)](#3-layered-architecture-mandatory)
4. [Repository structure](#4-repository-structure)
5. [Application boundaries](#5-application-boundaries)
6. [Porterchain API (orchestrator)](#6-porterchain-api-orchestrator)
7. [Communication rules](#7-communication-rules)
8. [Fleetbase adapter](#8-fleetbase-adapter)
9. [Database ownership](#9-database-ownership)
10. [Domain lifecycles](#10-domain-lifecycles)
11. [Pricing, billing, notifications](#11-pricing-billing-notifications)
12. [Event bus](#12-event-bus)
13. [Fleetbase responsibilities](#13-fleetbase-responsibilities)
14. [Stripe rules](#14-stripe-rules)
15. [Security](#15-security)
16. [Observability](#16-observability)
17. [Reference numbers](#17-reference-numbers)
18. [Architecture decision records](#18-architecture-decision-records)
19. [Cursor development rules](#19-cursor-development-rules)
20. [Golden rules](#20-golden-rules)
21. [Simplification & essential complexity](#21-simplification--essential-complexity)
22. [Appendix A — Status mappings](#appendix-a--status-mappings)
23. [Appendix B — Integration health](#appendix-b--integration-health)
24. [Appendix C — Documentation simplification program](#appendix-c--documentation-simplification-program)
25. [Appendix D — Phase alignment checklist](#appendix-d--phase-alignment-checklist-zero-complexity)

---

## 1. Locked architecture

```
               PORTERCHAIN

               Website (Next.js)
                      │
                      ▼
            Booking / Customer Portal
                      │
                      ▼
              Merchant Portal
                      │
                      ▼
                Admin Portal (Business)
                      │
                      ▼
          Porterchain API (FastAPI)          ← "Logistics Orchestrator"
                      │
      ┌───────────────┼────────────────┐
      │               │                │
      ▼               ▼                ▼
 Pricing         Billing        Notification
 Engine          Engine          Engine
 (modules)       (modules)       (modules)

      │               │                │
      └───────────────┼────────────────┘
                      │
               Internal Event Bus
                      │
                      ▼
            Fleetbase Adapter Layer
                      │
                      ▼
                 Fleetbase Core
          (Dispatch / Driver / GPS /
           Routes / Tracking / POD)

                      │
                      ▼
                Driver Mobile App
```

This topology is **locked**. Do not redesign it without updating this document (§20).

---

## 2. Core principles

| Principle               | Rule                                                                                                                            |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| Product ownership       | **Porterchain is the product.** All commercial and customer-facing logic lives here.                                            |
| Execution engine        | **Fleetbase is the logistics execution engine only.** Dispatch, GPS, routes, POD — not CRM, pricing, or billing.                |
| Single integration path | **Never bypass the Fleetbase Adapter.** No frontend or API code calls Fleetbase HTTP directly.                                  |
| Upstream preservation   | Keep Fleetbase as close to upstream open source as possible.                                                                    |
| No duplication          | Reuse existing modules. Do not copy business rules into UI, routers, or adapters.                                               |
| Server-side truth       | Booking drafts, quotes, payments, and order state are **database-persisted**. Never rely on browser storage for business state. |

---

## 3. Layered architecture (mandatory)

Every feature must respect this separation. **Violations are architecture defects.**

### 3.1 The five rules

| Layer                    | Responsibility                                                                           | Must NOT contain                                                     |
| ------------------------ | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **UI**                   | Render data, capture input, call Porterchain API                                         | Business rules, pricing logic, payment verification, Fleetbase calls |
| **Controllers**          | Authenticate, validate input, call one Application Service, return response              | Business rules, SQL, external HTTP                                   |
| **Application Services** | **All business logic** — state machines, pricing decisions, orchestration, domain events | Direct Fleetbase HTTP (use adapter via service)                      |
| **Repositories**         | Persistence only — CRUD, queries, transactions                                           | Business rules, HTTP, UI concerns                                    |
| **Adapters**             | External integration only — map DTOs, auth, retries, webhooks                            | Business rules, Porterchain domain decisions                         |

```
UI  →  Controller  →  Application Service  →  Repository  →  Database
                              │
                              ├── Event Bus (async side effects)
                              └── Adapter  →  External system (Fleetbase, Stripe, …)
```

### 3.2 How this maps to the PCD repo

| Layer                    | Porterchain location                                                                                               | Examples                                                                         |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------- |
| **UI**                   | `website/`, `apps/admin/`, `apps/merchant-portal/`, `apps/driver-portal/`                                          | Pages, components, `lib/api.ts` fetch clients                                    |
| **Controllers**          | `apps/api/src/porterchain_api/routers/`                                                                            | `quotes.py`, `merchant.py`, `admin.py`, `webhooks.py`                            |
| **Application Services** | `apps/api/src/porterchain_api/*_engine/*_service.py`                                                               | `BookingService`, `QuoteService`, `MerchantBillingService`, `AdminOrdersService` |
| **Repositories**         | `apps/api/src/porterchain_api/models.py`, `*_models.py`, `pricing_engine/repository.py`                            | SQLAlchemy models; `SqlAlchemyPricingRepository`                                 |
| **Adapters**             | `services/fleetbase-adapter/`, `services/stripe_service.py` (API wrapper), `services/python/porterchain_services/` | `FleetbaseAdapter`, Stripe checkout, notification delivery                       |

### 3.3 Controller pattern (FastAPI routers)

Routers **orchestrate only**:

1. Resolve auth (`get_clerk_user_id`, `get_admin_context`, …)
2. Parse and validate request body (Pydantic schemas)
3. Call **one** Application Service method
4. Map result to response schema or HTTP error

```python
# Correct — router delegates to service
@router.post("/bookings")
def post_booking(body: StartBookingRequest, db: Session = Depends(get_db), ...):
    quote, customer, checkout_url = _booking_service.start_booking(db, settings, ...)
    return BookingResponse(...)

# Wrong — business logic in router
@router.post("/bookings")
def post_booking(...):
    if quote.state != "QUOTE":          # ← belongs in BookingService
        raise HTTPException(...)
    quote.customer_id = customer.id     # ← belongs in BookingService
```

### 3.4 Application Service pattern

Services own:

- Domain state transitions (quote → payment → booking confirmed)
- Validation and invariants
- Emitting domain events (`emit_event` in `booking_engine/_core.py`)
- Coordinating repositories and adapters

Services live under `*_engine/` packages:

| Package             | Domain                                                        |
| ------------------- | ------------------------------------------------------------- |
| `booking_engine/`   | Retail quote, draft, booking, payment, confirmation, tracking |
| `merchant_engine/`  | B2B bookings, billing, bulk, API keys                         |
| `admin_engine/`     | Ops, CRM, finance, drivers, pricing admin                     |
| `fleetbase_engine/` | Sync jobs, webhook processing, retry queue                    |
| `driver_engine/`    | Driver platform bridge                                        |

### 3.5 Repository pattern

- **ORM models** in `models.py`, `crm_models.py`, `booking_draft_models.py`, etc.
- **Queries** belong in repository classes or thin data-access helpers — not in routers.
- Repositories return entities; they do not decide business outcomes.

### 3.6 Adapter pattern

- **Fleetbase:** all HTTP via `services/fleetbase-adapter/` → factory in `services/fleetbase_integration.py`
- **Stripe:** checkout creation and webhook parsing in `services/stripe_service.py`; payment lifecycle in `PaymentService`
- Adapters translate between external APIs and Porterchain DTOs. They never own booking or pricing rules.

### 3.7 UI pattern

- Fetch from Porterchain API only (`NEXT_PUBLIC_PORTERCHAIN_API_URL` → `:8001`)
- Local quote preview on website is **estimation only**; server validates before payment (§11)
- No `fetch('http://localhost:8000/...')` to Fleetbase from any frontend

### 3.8 Where business logic must never live

| Location                      | Why forbidden                                 |
| ----------------------------- | --------------------------------------------- |
| React components / pages      | UI renders and submits; services decide       |
| `routers/*.py`                | Controllers orchestrate only                  |
| `models.py` / repositories    | Persistence only                              |
| `services/fleetbase-adapter/` | Integration mapping only                      |
| Fleetbase PHP/Ember code      | Execution engine only — not Porterchain rules |

---

## 4. Repository structure

### 4.1 Target layout

```
porterchain/
├── website/                    # Public site + booking (:3000)
├── apps/
│   ├── api/                    # Porterchain API (:8001)
│   ├── admin/                  # Business admin (:3002)
│   ├── merchant-portal/        # B2B portal (:3001)
│   ├── driver-portal/          # Driver web (:3003)
│   ├── worker/                 # Event bus + queue consumer
│   ├── customer/               # Retail portal (:3004)
│   ├── mobile-driver/          # Expo driver app
│   ├── mobile-customer/        # Expo customer app
│   └── fleetbase/              # Upstream clone — DO NOT MODIFY
├── packages/                   # Shared TS: ui, types, auth, events, config
├── services/
│   ├── fleetbase-adapter/      # Sole Fleetbase boundary
│   ├── event-bus/              # porterchain_event_bus
│   ├── pricing-engine/         # porterchain_pricing (library)
│   ├── driver-platform/        # Driver domain library
│   └── python/                 # porterchain_services (stripe, notifications, …)
├── shared/python/              # porterchain_shared
├── infrastructure/docker/      # Compose, Fleetbase overlays
├── env/                        # Environment templates
└── docs/                       # Documentation index
```

### 4.2 Path aliases (current vs target)

| Target                  | Current canonical path                           | Status                     |
| ----------------------- | ------------------------------------------------ | -------------------------- |
| `apps/website/`         | `website/`                                       | Active (migration planned) |
| `apps/merchant/`        | `apps/merchant-portal/`                          | Active                     |
| `apps/customer/`        | `apps/customer/` + `website/.../portal/customer` | Active                     |
| `apps/admin/`           | `apps/admin/`                                    | Active                     |
| `apps/api/`             | `apps/api/`                                      | Active                     |
| `apps/driver/`          | `apps/driver-portal/` + `apps/mobile-driver/`    | Active                     |
| `apps/mobile-customer/` | `apps/mobile-customer/`                          | Active                     |

Full detail: [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md).

---

## 5. Application boundaries

| Application     | Port        | Calls Fleetbase? | Role                                                         |
| --------------- | ----------- | ---------------- | ------------------------------------------------------------ |
| Website         | 3000        | **No**           | Marketing, SEO, booking entry, tracking                      |
| Merchant portal | 3001        | **No**           | B2B bookings, bulk, billing, API keys                        |
| Admin           | 3002        | **SSO only**     | CRM, ops, finance, pricing — opens Fleetbase console via SSO |
| Driver portal   | 3003        | **No**           | Driver web dashboard → Porterchain API                       |
| Customer portal | 3004        | **No**           | Retail customer dashboard → Porterchain API                  |
| Mobile driver   | Expo        | **No**           | Field execution → `/driver-api/v1/*`                         |
| Mobile customer | Expo        | **No**           | Retail mobile → `/v1/*`                                      |
| Porterchain API | 8001        | **Via adapter**  | All business logic and orchestration                         |
| Fleetbase       | 8000 / 4200 | N/A              | Dispatch, GPS, routes, POD                                   |

### 5.1 Portal responsibilities

**Website** — Marketing, SEO, quote entry, authentication entry, public tracking, booking widget.

**Booking / Customer portal** — Booking draft lifecycle, checkout, Stripe redirect, booking history, invoices, receipts. Available via `website/` routes and standalone `apps/customer/` (:3004) plus `apps/mobile-customer/`.

**Merchant portal** — Business bookings, CSV/XLSX uploads, recipients, addresses, reports, API keys, NET billing.

**Admin portal** — CRM, merchants, drivers, fleet ops, finance, pricing, contracts, analytics, documents, support, booking drafts. **Admin never calls Fleetbase APIs directly** — only Porterchain API and SSO to Fleetbase console.

---

## 6. Porterchain API (orchestrator)

The API at `apps/api/` is the **Logistics Orchestrator** in the locked diagram. Code name: **Porterchain API** (`:8001`).

### 6.1 Engine modules (Application Services home)

| Engine                 | Responsibility                                                 |
| ---------------------- | -------------------------------------------------------------- |
| `booking_engine/`      | Quote, booking draft, booking, payment, confirmation, tracking |
| `billing_engine/`      | Settlement ledger, async billing queue processing              |
| `notification_engine/` | Templates, delivery logs, email/SMS/push queueing              |
| `merchant_engine/`     | B2B lifecycle, merchant billing, bulk, dashboard               |
| `admin_engine/`        | Ops, CRM, finance, claims, pricing admin, RBAC                 |
| `fleetbase_engine/`    | Outbound sync, inbound webhooks, retry, audit                  |
| `driver_engine/`       | Driver auth and Fleetbase bridge                               |
| `pricing_engine/`      | Bridge to `services/pricing-engine`                            |

Billing and notification **engines** live in `billing_engine/` and `notification_engine/` (embedded in API monolith). Merchant-specific billing views remain in `merchant_engine/`.

### 6.2 Async worker

`apps/worker/` consumes the event bus and task queues (email, SMS, push, billing). No HTTP port.

---

## 7. Communication rules

Every request follows:

```
UI (Next.js)
    ↓  HTTPS /v1/*
FastAPI Router (Controller)
    ↓
Application Service
    ↓
Repository → Database
    ↓ (when async / side effect)
Event Bus → Worker
    ↓ (when logistics execution)
Fleetbase Adapter → Fleetbase API
```

**Hard rules:**

- No UI may call Fleetbase directly.
- No router may call Fleetbase HTTP directly — use `fleetbase_engine` + adapter.
- Webhooks (Stripe, Fleetbase) enter via `routers/webhooks.py` and delegate to services immediately.

---

## 8. Fleetbase adapter

**Path:** `services/fleetbase-adapter/` (`porterchain_fleetbase_adapter`)

**Factory:** `apps/api/src/porterchain_api/services/fleetbase_integration.py`

| Responsibility                    |
| --------------------------------- |
| Authentication                    |
| Order, driver, vehicle mapping    |
| Tracking and status translation   |
| Webhook processing                |
| Retry queue and error handling    |
| Logging and version compatibility |
| Health monitoring                 |

Deprecated shim: `services/fleetbase/` — do not add new code there.

---

## 9. Database ownership

### Porterchain database owns

Customers, visitors, merchants, quotes, booking drafts, bookings, orders, contracts, pricing config, invoices, payments, receipts, CRM, analytics, support tickets, notifications, documents, audit logs, domain events.

### Fleetbase database owns

Drivers (operational), vehicles, dispatch, routes, GPS traces, waypoints, proof of delivery, fleet operations.

Commercial data stays in Porterchain unless Fleetbase requires a field for execution.

---

## 10. Domain lifecycles

### 10.1 Retail booking lifecycle

```
Visitor
  → Quote
  → Booking Draft (persisted — never browser-only)
  → Clerk authentication + session merge
  → Booking draft restore
  → Stripe Checkout
  → Stripe webhook verification (only trusted payment signal)
  → Booking confirmed → Order created
  → Fleetbase order (via event bus + adapter)
  → Dispatch → Delivery → POD
  → Invoice closed
```

### 10.2 Booking draft states

| State                 | Meaning                                                |
| --------------------- | ------------------------------------------------------ |
| `DRAFT`               | Partial data saved server-side                         |
| `QUOTE_GENERATED`     | Quote attached                                         |
| `CUSTOMER_IDENTIFIED` | Session merged to customer                             |
| `AUTHENTICATED`       | Clerk auth complete                                    |
| `PAYMENT_PENDING`     | Stripe Checkout started                                |
| `PAYMENT_FAILED`      | Payment failed or abandoned                            |
| `PAYMENT_COMPLETED`   | Webhook verified payment                               |
| `BOOKING_CONFIRMED`   | Booking + order created                                |
| `CANCELLED`           | Explicitly cancelled                                   |
| `EXPIRED`             | Timed out — kept for analytics; may resume if extended |

Every transition is audited. Implementation: `booking_draft_models.py`, `BookingDraftService`.

---

## 11. Pricing, billing, notifications

### 11.1 Pricing

| Rule                  | Detail                                                            |
| --------------------- | ----------------------------------------------------------------- |
| Website estimate      | Client engine (`website/src/lib/pricing/`) is for UX preview only |
| Authoritative pricing | Server `services/pricing-engine/` before payment                  |
| Re-validation         | Validate again at checkout and in `PaymentService`                |
| Contracts             | Merchant contract pricing overrides public retail                 |

### 11.2 Billing (modules — target: Billing Engine)

Managed by Application Services + Stripe adapter:

- Stripe Checkout and webhooks
- Invoices, receipts, refunds, credit notes
- Merchant NET billing and statements
- Driver payouts (future)

**Future scope (not yet implemented):** credit notes, partial refunds beyond Stripe webhooks, and scheduled driver payout batches. These remain on the roadmap; retail checkout invoices/receipts are live via `BookingConfirmationService` + Stripe.

Key services: `PaymentService`, `BookingConfirmationService`, `MerchantBillingService`, `AdminFinanceService`.

### 11.3 Notifications (modules — target: Notification Engine)

- Email (log-only locally without SMTP), SMS (Twilio optional), Firebase push (requires credentials in prod)
- Event-driven via `NotificationService` + event bus handlers
- Delivery through `apps/worker/` queues
- Templates, retry, delivery logs

---

## 12. Event bus

**Path:** `services/event-bus/` (`porterchain_event_bus`)

**Bridge:** `apps/api/src/porterchain_api/platform/bus.py`

| Requirement                                                   |
| ------------------------------------------------------------- |
| Domain events for all significant state changes               |
| Idempotency on webhook and payment handlers                   |
| Retries and dead-letter queue support                         |
| Redis Streams in production; in-memory fallback for local dev |

**Example events:** `quote.created`, `booking.draft_restored`, `payment.succeeded`, `booking.confirmed`, `order.dispatch_ready`, `fleetbase.order_created`, `invoice.created`.

Catalog: `apps/api/src/porterchain_api/booking_engine/events.py`, `shared/python/porterchain_shared/events/`.

---

## 13. Fleetbase responsibilities

### Fleetbase owns (execution only)

Driver management, vehicles, dispatch, route optimization, live GPS, waypoints, POD, driver status, delivery status, geofencing, operational maps, navigation, dispatch queue.

### Fleetbase never owns

CRM, pricing, billing, contracts, Stripe, merchant accounts, booking drafts, invoices, analytics, support tickets, audit logs.

---

## 14. Stripe rules

- Use **Stripe Checkout** for retail payments.
- **Only Stripe webhooks** finalize payment and create bookings/orders.
- Never trust frontend payment success alone.
- Never store card data (PCI).
- Record Payment Intent ID, checkout session ID, and transaction references on `Payment` rows.
- Booking draft must reach `PAYMENT_COMPLETED` only after verified webhook.

---

## 15. Security

- **Clerk** for authentication (website, merchant, admin, driver portals).
- **JWT validation** on API (`auth/clerk.py`).
- **RBAC** for admin and merchant (`admin_engine/rbac.py`, `merchant_engine/rbac.py`).
- **Webhook signature verification** (Stripe, Fleetbase).
- **Secrets** in environment / secret manager — never in repo.
- **Audit logs** for booking draft transitions, admin actions, domain events.
- **Least privilege** on all service accounts.

---

## 16. Observability

| Area         | Requirement                                                 |
| ------------ | ----------------------------------------------------------- |
| Logging      | Structured logs with correlation IDs on requests and events |
| Queues       | Monitor worker queue depth and DLQ                          |
| Integrations | Health checks for Fleetbase, Stripe, Redis, PostgreSQL      |
| Metrics      | API latency, webhook success rate, dispatch sync failures   |
| Retries      | Alert on exhausted Fleetbase sync retries                   |

---

## 17. Reference numbers

| Entity   | Format example    |
| -------- | ----------------- |
| Booking  | `PCB-2026-000001` |
| Tracking | `PCT-2026-000001` |
| Invoice  | `PCI-2026-000001` |
| Merchant | `PCM-000001`      |
| Driver   | `PCD-000001`      |
| Vehicle  | `PCV-000001`      |

Generator: `apps/api/src/porterchain_api/booking_engine/numbers.py`.

---

## 18. Architecture decision records

| ADR     | Decision                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| ADR-001 | Fleetbase is the execution engine only                                                                                               |
| ADR-002 | Porterchain owns all business logic                                                                                                  |
| ADR-003 | Fleetbase Adapter is mandatory — no direct Fleetbase calls                                                                           |
| ADR-004 | Booking Draft is mandatory — server-persisted, no browser-only state                                                                 |
| ADR-005 | Event Bus is mandatory for async side effects                                                                                        |
| ADR-006 | Stripe webhook is the only payment finalization signal                                                                               |
| ADR-007 | Layered architecture — business logic only in Application Services (§3)                                                              |
| ADR-008 | **Monolith-first modular boundaries** — one API; package by domain, not microservice ceremony                                        |
| ADR-009 | **Essential documentation only** — masterrule + canonical docs + OpenAPI; pointers replace duplicates (§21)                          |
| ADR-010 | **Phase 2 = strategies, not services** — AI dispatch, dynamic pricing, predictive ETA plug into existing engines (§21.4, Appendix D) |

---

## 19. Cursor development rules

Before implementing anything:

1. **Read this file** and [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) if touching architecture.
2. **Search** for existing services, routers, and adapters — reuse before creating.
3. **Place code in the correct layer** (§3) — never add business logic to UI or routers.
4. **Preserve** the locked topology (§1) and communication rules (§7).
5. **Avoid duplicate logic** — extend `*_engine` services, not parallel implementations.
6. **Document** intentional architectural changes here before merging.
7. **Simplify before expanding** — read §21; defer non-logistics features until dispatch E2E is boring.

---

## 20. Golden rules

1. Do not redesign the locked architecture without updating this document.
2. Do not bypass the Fleetbase Adapter.
3. Keep **all business logic** in Application Services (§3).
4. Keep Fleetbase close to upstream — no Porterchain rules in Fleetbase code.
5. Prefer refactoring over rewriting.
6. Maintain modularity within `*_engine` packages.
7. Keep APIs backward compatible where practical.
8. Every new feature must fit this architecture and layered rules.
9. UI renders only; controllers orchestrate only; repositories persist only; adapters integrate only.
10. Update this document before any intentional architectural change.
11. **Essential complexity only** — if removing it still delivers the shipment, defer or delete it (§21).
12. **One customer surface** — website for anonymous book/track; `apps/customer` (+ mobile) for authenticated retail; do not duplicate dashboards.
13. **Thin routers** — no new business logic in `routers/*.py`; extract Application Services.
14. **No upward imports** — `merchant_engine` must not depend on `admin_engine`; use shared domain modules.
15. **Docs follow code** — update canonical doc or OpenAPI when behavior changes; do not add parallel pointer files (§21, Appendix C).

---

## 21. Simplification & essential complexity

_Inspired by evolutionary architecture, bounded contexts, and monolith-first delivery (Martin Fowler). Porterchain is a **logistics company** first; the codebase must optimize for **quote → pay → dispatch → deliver → POD**._

### 21.1 Essential vs accidental

| Essential (keep)                                | Accidental (defer, pointer, or delete)                        |
| ----------------------------------------------- | ------------------------------------------------------------- |
| Booking draft, quote, Stripe, order state       | Duplicate customer portals on website + `:3004`               |
| Fleetbase adapter + sync + webhooks             | CRM sales pipelines before dispatch is reliable               |
| Merchant bulk, API keys, webhooks               | Route Center → Fleetbase optimize before sync backlog cleared |
| Driver execution, POD, GPS                      | 200+ markdown files that repeat the same topology             |
| Pricing (Valhalla/OSRM), billing, notifications | Fat routers (`admin.py` ~2000 lines) instead of services      |
| Clerk auth, RBAC                                | `merchant_engine` importing `admin_engine`                    |
| PostgreSQL as commercial truth                  | Optional module scores and conflicting readiness %            |

### 21.2 Patterns we follow

| Pattern                   | Application in Porterchain                                                    |
| ------------------------- | ----------------------------------------------------------------------------- |
| **Anti-Corruption Layer** | `services/fleetbase-adapter/` — keep; never call Fleetbase from UI            |
| **Monolith first**        | Single FastAPI `:8001` — do not split into microservices prematurely          |
| **Bounded context**       | Booking, Order, Merchant, Driver, Billing — enforce import direction          |
| **Strangler fig**         | Fleetbase replaces manual dispatch gradually; Porterchain stays product owner |
| **Branch by abstraction** | Event bus + worker **or** synchronous handlers — pick one production mode     |
| **YAGNI**                 | No new `*_engine` package without an Application Service and tests            |

### 21.3 Code simplification priorities

| Priority | Action                                                                | Outcome unchanged           |
| -------- | --------------------------------------------------------------------- | --------------------------- |
| P0       | Fleetbase sync UX — unsynced orders visible; replay dead letters      | Orders still reach dispatch |
| P1       | Thin `routers/admin.py`, `merchant.py`, `driver.py`                   | Same HTTP API (`/docs`)     |
| P1       | Extract shared `order` / `support` domain; fix merchant→admin imports | Same merchant features      |
| P2       | One authenticated customer app; website links out                     | Same retail journeys        |
| P2       | Worker in prod compose **or** document sync-only mode                 | Same notifications path     |
| P3       | Delete orphan `services/booking.py`; collapse pricing import path     | Same quotes                 |

### 21.4 Phase 1 vs Phase 2 (Uber 3.0 for B2B logistics)

**Vision:** Porterchain = orchestration platform for business logistics. Phase 1 ships the **shipment loop**. Phase 2 adds intelligence **without** new surfaces or microservices.

#### Phase 1 — ship today (essential)

| Actor              | Surface                                                                      | API prefix                             | Must do                                                                       |
| ------------------ | ---------------------------------------------------------------------------- | -------------------------------------- | ----------------------------------------------------------------------------- |
| Anonymous / retail | `website/` (quote, book, track) + `apps/customer/` + `apps/mobile-customer/` | `/v1/*`                                | Quote → pay → track; **no** duplicate dashboard on website                    |
| Merchant           | `apps/merchant-portal/`                                                      | `/v1/merchant/*`, `/v1/merchant-api/*` | Dashboard, bulk, billing, API keys, webhooks                                  |
| Driver             | `apps/driver-portal/` + `apps/mobile-driver/`                                | `/driver-api/v1/*`                     | Accept job, GPS, POD, offline                                                 |
| Ops (internal)     | `apps/admin/` control tower only                                             | `/v1/admin/*`                          | Dispatch board, orders, Fleetbase sync health, finance — **not** CRM pipeline |
| Execution          | Fleetbase via adapter                                                        | webhooks + sync                        | Dispatch, routing, live GPS, POD mirror                                       |
| Platform           | `apps/api/` monolith                                                         | OpenAPI `/docs`                        | Billing (Stripe), notifications, public API                                   |

**One core loop (only path that matters):**

```text
Quote → Booking draft → Stripe pay → Order (PostgreSQL) → Fleetbase dispatch
  → Driver execution → GPS/track → POD → Invoice/settlement → Merchant webhooks
```

#### Phase 2 — design for, build later (accidental if done early)

| Capability                                 | Rule                                                               |
| ------------------------------------------ | ------------------------------------------------------------------ |
| AI dispatch                                | New **strategy** behind existing dispatch port — no new admin app  |
| Predictive ETA                             | Read model + events — no duplicate tracking UI                     |
| Dynamic pricing                            | Extension to `porterchain_pricing` — same quote API                |
| Analytics / fleet mgmt                     | Read APIs + admin widgets — no Reports BI center                   |
| Mixed fleet (human, van, robot, drone, AV) | `FleetExecutor` ACL behind adapter — Fleetbase today, others later |

#### Future-proof hooks (allowed in Phase 1 code)

- `services/fleetbase-adapter/` as **template** for any executor (anti-corruption layer).
- `EVENT_CATALOG.md` + versioned envelopes for machine-readable dispatch decisions.
- `Order.assigned_executor_type` (or metadata JSON) — do not hard-code “driver only” in UI strings only.
- OpenAPI + `merchant-api` as the **integration contract** for partners and future AI agents.

Do **not** add Phase 2 packages (`ai_dispatch_engine`, `analytics_engine`, etc.) until Phase 1 loop is boring in production.

### 21.5 Simplification process (repeat every sprint)

1. **Name the essential journey** — one sentence: quote → POD for merchant + retail.
2. **One surface per actor** — delete duplicate UX (website customer portal vs `:3004`).
3. **Delete or defer** — if removing it still delivers the shipment, remove it (CRM pipeline, Route Center optimizer, BI center).
4. **Bounded contexts** — `merchant_engine` must not import `admin_engine`; shared code lives in `domain/` or `order_engine/`.
5. **Thin routers** — HTTP adapters only; logic in `*_engine` application services.
6. **One async mode** — API inline handlers **or** worker queues in prod, not both silently.
7. **Contract = OpenAPI** — markdown describes why; `/docs` describes routes.

Track execution in **[Appendix D](#appendix-d--phase-alignment-checklist-zero-complexity)**.

### 21.6 Documentation standard (every `.md` file)

Each file in the repo (except `website/content/blog/*` and `docs/archive/*`) must declare:

```markdown
**Type:** CANONICAL | POINTER | REPORT | README
**masterrule:** §… or link
**Last verified:** YYYY-MM-DD
```

| Type          | Rule                                                                                     |
| ------------- | ---------------------------------------------------------------------------------------- |
| **CANONICAL** | Single source for a topic; must match code and OpenAPI; updated when behavior changes    |
| **POINTER**   | ≤15 lines: title, type, canonical link(s), archive link; **no unique technical content** |
| **REPORT**    | Generated or point-in-time audit; link to canonical doc for current truth                |
| **README**    | How to run/build that folder only; link to masterrule for architecture                   |

**Canonical set (do not duplicate):** this file, [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md), [INTEGRATIONS.md](./INTEGRATIONS.md), [EVENT_CATALOG.md](./EVENT_CATALOG.md), [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md), [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md), [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md), [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md), [CTO_AUDIT_REPORT.md](./CTO_AUDIT_REPORT.md), OpenAPI `/docs`.

### 21.7 Rollout

Improve **all** platform docs in **groups of five** (Appendix C). For each group:

1. Classify each file (CANONICAL / POINTER / REPORT / README).
2. POINTER → trim to template; REPORT → add “regenerable / snapshot” banner.
3. CANONICAL → remove duplication; link to code paths and OpenAPI.
4. Mark group **Done** in Appendix C when merged.

Do **not** create new root-level audit files — extend canonical docs or [CTO_AUDIT_REPORT.md](./CTO_AUDIT_REPORT.md).

---

## Appendix A — Status mappings

### Porterchain order state → Fleetbase status

| Porterchain      | Fleetbase    |
| ---------------- | ------------ |
| Waiting dispatch | `pending`    |
| Assigned         | `assigned`   |
| Driver accepted  | `accepted`   |
| At pickup        | `arrived`    |
| Picked up        | `picked_up`  |
| In transit       | `in_transit` |
| Delivered        | `completed`  |
| Returned         | `returned`   |
| Cancelled        | `cancelled`  |

Translator: `fleetbase_engine/status_translator.py`, `fleetbase_engine/tracking_translator.py`.

---

## Appendix B — Integration health

Monitor in production; verify locally with `pnpm ports` and `pnpm docker:fleetbase:verify`.

| Integration        | Local endpoint / check           |
| ------------------ | -------------------------------- |
| Porterchain API    | `http://localhost:8001/health`   |
| Fleetbase API      | `http://localhost:8000`          |
| Fleetbase console  | `http://localhost:4200`          |
| Stripe             | Webhook + `STRIPE_MOCK` for dev  |
| Redis              | `127.0.0.1:6379`                 |
| PostgreSQL         | `127.0.0.1:5432`                 |
| Valhalla (routing) | `http://localhost:8002/status`   |
| OSRM (fallback)    | Configured in Fleetbase env      |
| Mailhog            | `http://localhost:8025`          |
| Background worker  | `pnpm dev:worker` — no HTTP port |

---

## Appendix C — Documentation simplification program

**Scope:** 191 platform markdown files (excludes `docs/archive/*`, `website/content/blog/*`, `.venv`).  
**Groups:** 39 × 5 files · **Status:** Phase 1 complete (July 2026)  
**Phase 0 (done):** §21.4 headers on all 191 files.  
**Phase 1 (done):** All 39 groups processed (2026-07-05).  
**Audit:** [CTO_AUDIT_REPORT.md](./CTO_AUDIT_REPORT.md)

### Per-group workflow

1. Open all five paths in the group row below.
2. Set **Type** header per §21.4.
3. POINTER files: replace body with canonical links only.
4. CANONICAL files: verify against code; add OpenAPI link where API is described.
5. Change group status from `Pending` → `Done` in this table when PR merges.

### Group index

| Group | Files                                                                                                                                                                                                                                                          | Status | Focus                                      |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ | ------------------------------------------ |
| G01   | `ALEMBIC_VALIDATION.md` · `API_DEPENDENCY_GRAPH.md` · `API_FLOW_DIAGRAM.md` · `API_FLOW_REPORT.md` · `API_TRACE_REPORT.md`                                                                                                                                     | Done   | Keep Alembic canonical; pointer API audits |
| G02   | `ARCHITECTURE_ALIGNMENT_REPORT.md` · `ARCHITECTURE_AUDIT.md` · `AUTHENTICATION.md` · `AUTHENTICATION_ARCHITECTURE.md` · `AUTHENTICATION_AUDIT.md`                                                                                                              | Done   | Auth cluster; one canonical                |
| G03   | `AUTHENTICATION_CLEANUP.md` · `AUTHENTICATION_FLOW.md` · `BOOKING_WORKFLOW_AUDIT.md` · `BUSINESS_GLOSSARY.md` · `BUSINESS_WORKFLOW.md`                                                                                                                         | Done   | Booking + glossary                         |
| G04   | `CLERK_INTEGRATION_REPORT.md` · `CONNECTIONS.md` · `CONTRIBUTING_GUIDE.md` · `CTO_AUDIT_REPORT.md` · `DATABASE_ARCHITECTURE.md`                                                                                                                                | Done   | Governance + DB canonical                  |
| G05   | `DATABASE_AUDIT.md` · `DATABASE_CONFIGURATION_REPORT.md` · `DATABASE_MIGRATION_PLAN.md` · `DATABASE_OWNERSHIP_MATRIX.md` · `DATABASE_VALIDATION_REPORT.md`                                                                                                     | Done   | DB reports → pointers                      |
| G06   | `DATA_CONSISTENCY_REPORT.md` · `DEPENDENCY_REPORT.md` · `DOCKER_ARCHITECTURE.md` · `DOCKER_SETUP.md` · `DOMAIN_MODEL.md`                                                                                                                                       | Done   | Ops + domain model                         |
| G07   | `DRIVER_ARCHITECTURE_REPORT.md` · `DRIVER_AUDIT.md` · `DRIVER_INTEGRATION_MATRIX.md` · `DRIVER_PERFORMANCE_REPORT.md` · `DRIVER_PLATFORM.md`                                                                                                                   | Done   | Driver module                              |
| G08   | `DRIVER_PRODUCTION_READINESS.md` · `DRIVER_SECURITY_REPORT.md` · `ENTITY_RELATIONSHIP_MODEL.md` · `ENVIRONMENT_VARIABLES.md` · `EVENT_BUS.md`                                                                                                                  | Done   | Driver readiness + events                  |
| G09   | `EVENT_BUS_AUDIT.md` · `EVENT_BUS_REPORT.md` · `EVENT_CATALOG.md` · `EVENT_FLOW.md` · `EVENT_FLOW_DIAGRAM.md`                                                                                                                                                  | Done   | Event bus canonical set                    |
| G10   | `EVENT_MATRIX.md` · `EXCEPTION_WORKFLOWS.md` · `EXTENSION_GUIDE.md` · `FAILURE_SCENARIOS_REPORT.md` · `FLEETBASE_ADAPTER_ARCHITECTURE.md`                                                                                                                      | Done   | Fleetbase adapter                          |
| G11   | `FLEETBASE_ANALYSIS.md` · `FLEETBASE_APIS.md` · `FLEETBASE_DATABASE.md` · `FLEETBASE_EVENTS.md` · `FLEETBASE_EXTENSION_POINTS.md`                                                                                                                              | Done   | Fleetbase detail → pointers                |
| G12   | `FLEETBASE_INSTALL.md` · `FLEETBASE_INTEGRATION.md` · `FLEETBASE_MODULES.md` · `FLEETBASE_SERVICE_STATUS.md` · `FLEETBASE_USAGE.md`                                                                                                                            | Done   | Fleetbase ops canonical                    |
| G13   | `FLEETBASE_WEBHOOKS.md` · `FOLDER_STRUCTURE.md` · `FORWARD_LOGISTICS_REPORT.md` · `GAP_ANALYSIS.md` · `GOOGLE_MAPS_REPORT.md`                                                                                                                                  | Done   | Gaps + maps reports                        |
| G14   | `GOOGLE_MAPS_USAGE.md` · `GOOGLE_MAPS_USAGE_REPORT.md` · `INTEGRATIONS.md` · `INTEGRATION_AUDIT.md` · `INVITATION_WORKFLOW.md`                                                                                                                                 | Done   | **INTEGRATIONS** hub                       |
| G15   | `MAPS_ARCHITECTURE_AUDIT.md` · `MASTERULE_COMPLIANCE_GAPS.md` · `MERCHANT_ARCHITECTURE_REPORT.md` · `MERCHANT_AUDIT.md` · `MERCHANT_COMPONENT_MATRIX.md`                                                                                                       | Done   | Merchant audits                            |
| G16   | `MERCHANT_GAP_ANALYSIS.md` · `MERCHANT_INTEGRATION_MATRIX.md` · `MERCHANT_PERFORMANCE_REPORT.md` · `MERCHANT_PRODUCTION_READINESS.md` · `MERCHANT_SECURITY_REPORT.md`                                                                                          | Done   | Merchant readiness                         |
| G17   | `MISSING_INTEGRATIONS.md` · `MOBILE_ARCHITECTURE.md` · `MOBILE_ARCHITECTURE_REPORT.md` · `MOBILE_DESIGN_SYSTEM.md` · `MOBILE_PERFORMANCE_REPORT.md`                                                                                                            | Done   | Mobile cluster                             |
| G18   | `MOBILE_PRODUCTION_READINESS.md` · `MOBILE_SECURITY_REPORT.md` · `MOBILE_UI_REPORT.md` · `MODULE_BREAKDOWN.md` · `MODULE_DEPENDENCY_GRAPH.md`                                                                                                                  | Done   | Mobile + modules                           |
| G19   | `MODULE_INTEGRATION_MATRIX.md` · `MODULE_SCORECARD.md` · `NOTIFICATION_REPORT.md` · `ORDER_LIFECYCLE.md` · `ORDER_LIFECYCLE_REPORT.md`                                                                                                                         | Done   | Order lifecycle                            |
| G20   | `OSRM_REPORT.md` · `OSRM_USAGE.md` · `PERFORMANCE_AUDIT.md` · `PLATFORM_FOUNDATION.md` · `PORTERCHAIN-LEGAL-AND-IMPORTANT-INFO.md`                                                                                                                             | Done   | Platform + legal                           |
| G21   | `PORT_CONFIGURATION.md` · `POSTGRESQL_COMPATIBILITY_REPORT.md` · `POSTGRESQL_PERFORMANCE.md` · `PRICING_ENGINE.md` · `PRODUCTION_DATABASE_SCORE.md`                                                                                                            | Done   | Ports + pricing                            |
| G22   | `PRODUCTION_READINESS_REPORT.md` · `PRODUCT_REQUIREMENTS.md` · `RBAC.md` · `RBAC_MATRIX.md` · `README.md`                                                                                                                                                      | Done   | **README** + go/no-go                      |
| G23   | `REALTIME_COMMUNICATION_REPORT.md` · `REPOSITORY_STRUCTURE.md` · `REVERSE_LOGISTICS_REPORT.md` · `ROADMAP.md` · `ROLE_PERMISSIONS.md`                                                                                                                          | Done   | Repo + roadmap                             |
| G24   | `ROUTE_CENTER_ARCHITECTURE.md` · `ROUTE_CENTER_AUDIT.md` · `ROUTE_CENTER_INTEGRATION.md` · `ROUTE_CENTER_PERFORMANCE.md` · `ROUTING_ENGINE_AUDIT.md`                                                                                                           | Done   | Route Center                               |
| G25   | `RUNBOOK.md` · `SECURITY.md` · `SECURITY_AUDIT.md` · `SERVICE_STATUS.md` · `SQLITE_AUDIT.md`                                                                                                                                                                   | Done   | Security + runbook                         |
| G26   | `SSO.md` · `SYSTEM_ARCHITECTURE.md` · `SYSTEM_SEQUENCE_DIAGRAMS.md` · `SYSTEM_VALIDATION_REPORT.md` · `TECH_STACK.md`                                                                                                                                          | Done   | Topology pointers                          |
| G27   | `UPGRADE_GUIDE.md` · `USER_JOURNEYS.md` · `VALHALLA_REPORT.md` · `VALHALLA_USAGE.md` · `apps/admin/README.md`                                                                                                                                                  | Done   | Journeys + Valhalla                        |
| G28   | `apps/api/README.md` · `apps/api/alembic/README.md` · `apps/customer/README.md` · `apps/driver/README.md` · `apps/merchant-portal/README.md`                                                                                                                   | Done   | App READMEs (API)                          |
| G29   | `apps/merchant/README.md` · `apps/mobile-customer/.expo/README.md` · `apps/mobile-customer/README.md` · `apps/mobile-driver/README.md` · `apps/website/README.md`                                                                                              | Done   | App READMEs (mobile)                       |
| G30   | `apps/worker/README.md` · `docs/README.md` · `docs/architecture/ADMIN_CONTROL_TOWER.md` · `docs/architecture/API_DEPENDENCY.md` · `docs/architecture/APPLICATION_FLOW.md`                                                                                      | Done   | docs index + flows                         |
| G31   | `docs/architecture/ARCHITECTURE_VALIDATION_REPORT.md` · `docs/architecture/AUTHENTICATION_FLOW.md` · `docs/architecture/BOOKING_FLOW.md` · `docs/architecture/DATABASE_RELATIONSHIP.md` · `docs/architecture/DISPATCH_FLOW.md`                                 | Done   | Core flow diagrams                         |
| G32   | `docs/architecture/EVENT_BUS_FLOW.md` · `docs/architecture/FLEETBASE_FLOW.md` · `docs/architecture/GOOGLE_MAPS_FLOW.md` · `docs/architecture/MERCHANT_FLOW.md` · `docs/architecture/MODULE_DEPENDENCY.md`                                                      | Done   | Integration flows                          |
| G33   | `docs/architecture/NOTIFICATION_FLOW.md` · `docs/architecture/ORDER_LIFECYCLE.md` · `docs/architecture/OSRM_FLOW.md` · `docs/architecture/PAYMENT_FLOW.md` · `docs/architecture/README.md`                                                                     | Done   | Payment + order flows                      |
| G34   | `docs/architecture/REALTIME_FLOW.md` · `docs/architecture/REPORTING_FLOW.md` · `docs/architecture/SYSTEM_ARCHITECTURE.md` · `docs/architecture/VALHALLA_FLOW.md` · `docs/notifications/DEVICE_REGISTRATION_FLOW.md`                                            | Done   | **SYSTEM_ARCHITECTURE**                    |
| G35   | `docs/notifications/FCM_CONFIGURATION.md` · `docs/notifications/NOTIFICATION_ARCHITECTURE.md` · `docs/notifications/NOTIFICATION_DELIVERY_FLOW.md` · `docs/notifications/NOTIFICATION_EVENT_MATRIX.md` · `docs/notifications/NOTIFICATION_TEMPLATE_CATALOG.md` | Done   | Notifications                              |
| G36   | `docs/notifications/PUSH_NOTIFICATION_REPORT.md` · `env/README.md` · `infrastructure/deploy/README.md` · `masterrule.md` · `packages/config/README.md`                                                                                                         | Done   | Env + deploy + this file                   |
| G37   | `packages/shared/README.md` · `services/README.md` · `services/fleetbase-adapter/README.md` · `services/pricing-engine/README.md` · `shared/README.md`                                                                                                         | Done   | Package READMEs                            |
| G38   | `shared/config/README.md` · `shared/maps/MAP_MODULE.md` · `vendor/fleetbase/README.md` · `website/AGENTS.md` · `website/CLAUDE.md`                                                                                                                             | Done   | Shared + vendor                            |
| G39   | `website/README.md`                                                                                                                                                                                                                                            | Done   | Website README                             |

---

## Appendix D — Phase alignment checklist (zero complexity)

**Purpose:** Single execution tracker for Phase 1 (Uber 3.0 B2B logistics) with Phase 2 hooks only.  
**Method:** Martin Fowler — essential vs accidental complexity, monolith-first, bounded contexts, anti-corruption layers.  
**Last audited:** 2026-07-05 (repo scan after simplification pass)

**How to use:** Work top to bottom. Do not start Phase 2 items until every **P0** box in §D1–D3 is checked. Mark `[x]` when done in a merged PR.

### D0 — Target architecture (what “simple” looks like)

```text
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1 SURFACES (thin clients — zero business logic)          │
│  website (:3000)  merchant-portal (:3001)  customer (:3004)     │
│  mobile-customer  driver-portal (:3003)  mobile-driver          │
│  admin (:3002) = ops control tower ONLY                           │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / Clerk JWT
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  apps/api (:8001) — ONE MONOLITH                                 │
│  booking_engine │ merchant_engine │ driver_engine │ billing_*   │
│  fleetbase_engine │ pricing_engine │ notification_engine        │
│  domain/ │ order_engine/ (shared kernels — no upward imports)    │
└────────────────────────────┬────────────────────────────────────┘
                             │ adapter only
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  services/fleetbase-adapter/  →  Fleetbase (:8000) execution    │
│  (future: robot/drone/AV adapters implement same port)           │
└─────────────────────────────────────────────────────────────────┘

PostgreSQL = commercial truth │ Redis = bus/queues │ Stripe = payments
```

### D1 — P0 Production loop (nothing else until these pass)

**Local verification:** `pnpm fleetbase:replay` then `pnpm validate:p0` (see [RUNBOOK.md](./RUNBOOK.md#d1-p0--production-loop-checklist)).

- [x] **G1** Droplet/prod: API healthy, `booking_drafts` table exists, smoke test passes _(prod ✓ 2026-07-05 — `pnpm validate:p0:prod`)_
- [x] **G2** Fleetbase sync: >90% orders reach `fleetbase_order_id`; dead-letter replay documented _(local 31/31 = 100%; `pnpm fleetbase:replay` + RUNBOOK)_
- [x] **G3** `FLEETBASE_WEBHOOK_SECRET` set; webhook ingress verified _(local `.env` + signed POST)_
- [x] **G4** End-to-end local: quote → Stripe (mock) → order → dispatch event → Fleetbase order
- [x] **G5** Driver path: assign → GPS update → POD photo/signature → order `DELIVERED` _(simulated in E2E phase 2)_
- [x] **G6** Merchant path: bulk upload → order list → invoice/billing view
- [x] **G7** Customer path: book on website → pay → track on `apps/customer` or mobile (one dashboard)
- [x] **G8** Billing: Stripe webhook finalizes payment; invoice row created _(mock Stripe local)_
- [x] **G9** Notifications: email/push path works in chosen prod async mode _(prod Firebase live 2026-07-05 — `PORTERCHAIN_PUSH_ENABLED=true`, project `porterchain-55313`, service-account mounted at `/run/secrets/firebase-service-account.json`; `/health/ready` → `firebase: ok`)_

### D2 — Remove accidental complexity (codebase)

**Verify:** `pnpm validate:d2` (forbidden paths absent + customer/driver API contract alignment).

#### Surfaces — one per actor

- [x] Delete `website/src/app/**/portal/customer/**` (embedded retail dashboard)
- [x] Point website nav/footer to `NEXT_PUBLIC_CUSTOMER_PORTAL_URL` (`:3004`)
- [x] Confirm `apps/customer` is sole authenticated retail web app
- [x] Confirm `apps/mobile-customer` shares same `/v1/customers/*` contract _(via `@porterchain/mobile-api` / `shared/api`)_
- [x] Confirm `apps/driver-portal` + `apps/mobile-driver` share `/driver-api/v1/*` _(web proxy + `shared/api/src/driver.ts`)_
- [x] Delete stub folders `apps/merchant/`, `apps/driver/` (README-only) if still present

#### Admin — ops only, not a second product

- [x] Delete `apps/admin/src/app/(ops)/crm/**` (leads, deals, pipeline — Phase 2)
- [x] Delete `apps/admin/src/app/(ops)/routes/**` (Route Center — use Fleetbase + control tower)
- [x] Delete `apps/admin/src/app/(ops)/reports/**` (BI center — use module dashboards)
- [x] Admin nav: Control Tower, Orders, Merchants, Drivers, Finance, Support only
- [x] Keep `collaboration` API (`/v1/admin/collaboration`) for merchant/driver notes/tasks only
- [x] `lib/crm.ts` types-only (no `/v1/admin/crm` client); shared UI stays under `components/crm/`

#### API — deleted routers stay deleted

- [x] Remove `routers/crm.py` (full CRM API)
- [x] Remove `routers/route_center.py`
- [x] Remove `admin_engine/reports_service.py` (BI center)
- [x] Remove `admin_engine/route_center_service.py`, `dispatch_queue_optimizer.py`
- [x] Remove orphan `services/booking.py`
- [x] Remove `migrate_sqlite_to_postgres.py`, `seed_crm.py`
- [x] Remove stale `reporting_engine/` package if recreated; use `merchant_engine/reporting_metrics.py`
- [x] Remove HTTP E2E from `diagnostics.py` (keep `scripts/run_e2e_validation.py` only)

#### Bounded contexts — fix import direction

- [x] Extract `domain/support/` (ticket numbers, shared support helpers)
- [x] `merchant_engine/support_bridge_service.py` → use `domain/support` + `support_engine` (not `admin_engine`)
- [x] `merchant_engine/contacts_service.py` → use `domain/contacts` or `crm_models` repo, not `CrmSalesService` from admin
- [x] `booking_engine/customer_service.py` → no `admin_engine` imports
- [x] Collapse `services/pricing.py` into `pricing_engine` single entry point

#### Thin routers (same OpenAPI, less accidental logic)

- [x] Split `routers/admin.py` (~1800 lines) → sub-routers per module
- [x] Split `routers/merchant.py` (~1800 lines)
- [x] Split `routers/driver.py` (~1080 lines)
- [x] Rule: new endpoints → new application service method, not router logic

### D3 — Phase 1 feature matrix (must work)

**Verify:** `pnpm validate:d3` (contracts) · `pnpm validate:d3:e2e` (local) · `pnpm validate:d3:prod` (live URLs).

| Feature                      | Owner engine                                | Check                                          |
| ---------------------------- | ------------------------------------------- | ---------------------------------------------- |
| Merchant dashboard           | `merchant_engine`                           | [x] local + prod `validate:d3:prod` 2026-07-05 |
| Driver web + iOS + Android   | `driver_engine` + portals/mobile            | [x] local + prod portal 200                    |
| Customer web + iOS + Android | `booking_engine` + customer/mobile          | [x] local + prod quote + sign-in               |
| Dispatch                     | `fleetbase_engine` + admin operations       | [x] local · [ ] prod Fleetbase bridge off      |
| Routing                      | Valhalla/OSRM + Fleetbase                   | [x] local `validate:d3:e2e`                    |
| Tracking                     | public `/v1/orders/{tracking}` + websockets | [x] local + prod OpenAPI                       |
| Proof of delivery            | `driver_engine` + Fleetbase webhook         | [x] local · [ ] prod Fleetbase                 |
| Billing                      | `billing_engine` + Stripe                   | [x] local + prod Stripe configured             |
| Public / partner API         | `/v1/merchant-api/*` + OpenAPI              | [x] local + prod `/docs`                       |

**Prod manual smoke:** Clerk login on each portal; automated: `pnpm validate:d3:prod`.

### D4 — One async runtime (pick one, document in `RUNBOOK.md`)

- [x] **Option A (simpler prod):** API registers event handlers inline; worker only for retries/cron
- [ ] **Option B (scale):** Worker in prod compose; API publishes only; document queue ownership
- [x] Remove duplicate handler registration (today: API lifespan + worker both can register)
- [x] Prod compose lists worker OR documents sync-only mode explicitly _(RUNBOOK D4 + deploy README)_

### D5 — Phase 2 hooks only (no implementation yet)

- [x] Document `FleetExecutor` interface in `FLEETBASE_INTEGRATION.md` (human now; robot/drone/AV later)
- [x] Add `executor_type` to order metadata schema (migration when needed)
- [x] Event catalog entries stubbed for `dispatch.recommendation`, `eta.predicted` (no consumers)
- [x] ADR-010: Phase 2 capabilities are **strategies**, not new deployables
- [x] Do **not** add: AI dispatch UI, dynamic pricing UI, analytics warehouse, fleet solver in admin

### D6 — Documentation & contracts (zero doc sprawl)

- [x] Appendix C: 191 files typed (CANONICAL / POINTER / REPORT / README)
- [x] Update `SYSTEM_ARCHITECTURE.md`: admin = ops only; remove CRM/Route Center from component table
- [x] Pointer stale docs: `ROUTE_CENTER_ARCHITECTURE.md`, `MODULE_SCORECARD.md` route center rows
- [x] `apps/api/README.md` + OpenAPI = route truth for partner API
- [x] `PORT_CONFIGURATION.md` matches actual apps (no `apps/website` — use `website/`)

### D7 — Current audit snapshot (2026-07-05)

| Item                                             | Status                                                                        |
| ------------------------------------------------ | ----------------------------------------------------------------------------- |
| API CRM / route_center / reports routers         | Removed                                                                       |
| `collaboration` router + `collaboration_engine/` | Added                                                                         |
| Fat routers admin/merchant/driver                | **Split** into `routers/{admin,merchant,driver}/` packages                    |
| Admin CRM + Route Center UI                      | **Removed** (re-verified 2026-07-05)                                          |
| Website `/portal/customer`                       | **Removed** — links to `:3004`                                                |
| `merchant_engine` → `admin_engine` imports       | **Fixed** — `support_engine` + `domain/*`                                     |
| Fleetbase sync backlog (local audit)             | **Cleared** — 31/31 linked (100%) after replay                                |
| Prod droplet containers                          | **Live** — 8 services; `https://api.porterchain.com/health` → ok (2026-07-05) |
| D3 feature matrix                                | **Local + prod pass** — `validate:d3:e2e` + `validate:d3:prod` 2026-07-05     |
| Mobile customer + driver apps                    | Present in repo                                                               |
| Phase 2 AI/analytics code                        | Not started (good)                                                            |

### D8 — Suggested execution order (sprints)

1. ~~**Sprint A (P0 ops):** G1–G3 prod + Fleetbase sync replay~~ ✓ G1 prod live 2026-07-05
2. ~~**Sprint B (delete UI debt):** D2 surface + admin cleanup~~ ✓
3. ~~**Sprint C (boundaries):** D2 bounded-context extractions~~ ✓
4. ~~**Sprint D (routers):** D2 thin routers~~ ✓
5. ~~**Sprint E:** D3 prod smoke + portal URLs~~ ✓ `validate:d3:prod` 2026-07-05
6. ~~**Sprint F:** G9 Firebase secrets → enable `PORTERCHAIN_PUSH_ENABLED`~~ ✓ prod push live 2026-07-05; prod Fleetbase G2/G3 pending (when dispatch needed)
7. ~~**Sprint G (Phase 2 prep):** D5 hooks + ADR-010 only~~ ✓

---

## Related documents

| Document                                                                               | Purpose                        |
| -------------------------------------------------------------------------------------- | ------------------------------ |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)                     | Go/no-go certification         |
| [CTO_AUDIT_REPORT.md](./CTO_AUDIT_REPORT.md)                                           | Doc vs code audit              |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) | Platform topology              |
| [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)                                   | Monorepo layout and PYTHONPATH |
| [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)                                       | Local ports and start commands |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                                 | Adapter and sync flows         |
| [INTEGRATIONS.md](./INTEGRATIONS.md)                                                   | External systems matrix        |
| [EVENT_BUS.md](./EVENT_BUS.md)                                                         | Event bus design               |
| [AUTHENTICATION_ARCHITECTURE.md](./AUTHENTICATION_ARCHITECTURE.md)                     | Clerk and RBAC                 |

---

_Violations of §3 (layered architecture) should be fixed in refactor, not extended with new code in the wrong layer. Prefer simplification per §21 before adding new documents or modules._
