# Porterchain — Master Architecture Rules

**Version:** 3.1  
**Status:** APPROVED  
**Owner:** Ravi Chauhan  
**Last updated:** June 30, 2026

> This document is the **single source of truth** for Porterchain. Every Cursor prompt, feature, refactor, review, and integration must follow it.  
> For implementation status vs this diagram, see [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md).

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
21. [Appendix A — Status mappings](#appendix-a--status-mappings)
22. [Appendix B — Integration health](#appendix-b--integration-health)

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
│   └── fleetbase/              # Upstream clone (gitignored) — DO NOT MODIFY
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

| Target           | Current canonical path                           | Status                       |
| ---------------- | ------------------------------------------------ | ---------------------------- |
| `apps/website/`  | `website/`                                       | Active (migration planned)   |
| `apps/merchant/` | `apps/merchant-portal/`                          | Active                       |
| `apps/customer/` | `apps/customer/` + `website/.../portal/customer` | Active                       |
| `apps/admin/`    | `apps/admin/`                                    | Active                       |
| `apps/api/`      | `apps/api/`                                      | Active                       |
| `apps/driver/`   | `apps/driver-portal/` + `apps/mobile-driver/`    | Web + mobile scaffold active |

Full detail: [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md).

---

## 5. Application boundaries

| Application     | Port        | Calls Fleetbase? | Role                                                                  |
| --------------- | ----------- | ---------------- | --------------------------------------------------------------------- |
| Website         | 3000        | **No**           | Marketing, SEO, booking entry, tracking, customer dashboard (partial) |
| Merchant portal | 3001        | **No**           | B2B bookings, bulk, billing, API keys                                 |
| Admin           | 3002        | **SSO only**     | CRM, ops, finance, pricing — opens Fleetbase console via SSO          |
| Driver portal   | 3003        | **No**           | Driver web dashboard → Porterchain API                                |
| Porterchain API | 8001        | **Via adapter**  | All business logic and orchestration                                  |
| Fleetbase       | 8000 / 4200 | N/A              | Dispatch, GPS, routes, POD                                            |

### 5.1 Portal responsibilities

**Website** — Marketing, SEO, quote entry, authentication entry, public tracking, booking widget.

**Booking / Customer portal** — Booking draft lifecycle, checkout, Stripe redirect, booking history, invoices, receipts. Customer portal is embedded in website today; full `apps/customer/` is planned.

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

- Email, SMS, Firebase push (planned channels)
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

| ADR     | Decision                                                                |
| ------- | ----------------------------------------------------------------------- |
| ADR-001 | Fleetbase is the execution engine only                                  |
| ADR-002 | Porterchain owns all business logic                                     |
| ADR-003 | Fleetbase Adapter is mandatory — no direct Fleetbase calls              |
| ADR-004 | Booking Draft is mandatory — server-persisted, no browser-only state    |
| ADR-005 | Event Bus is mandatory for async side effects                           |
| ADR-006 | Stripe webhook is the only payment finalization signal                  |
| ADR-007 | Layered architecture — business logic only in Application Services (§3) |

---

## 19. Cursor development rules

Before implementing anything:

1. **Read this file** and [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md) if touching architecture.
2. **Search** for existing services, routers, and adapters — reuse before creating.
3. **Place code in the correct layer** (§3) — never add business logic to UI or routers.
4. **Preserve** the locked topology (§1) and communication rules (§7).
5. **Avoid duplicate logic** — extend `*_engine` services, not parallel implementations.
6. **Document** intentional architectural changes here before merging.

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

## Related documents

| Document                                                               | Purpose                        |
| ---------------------------------------------------------------------- | ------------------------------ |
| [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md) | Diagram vs current codebase    |
| [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)                   | Monorepo layout and PYTHONPATH |
| [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)                       | Local ports and start commands |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                 | Adapter and sync flows         |
| [EVENT_BUS.md](./EVENT_BUS.md)                                         | Event bus design               |
| [AUTHENTICATION.md](./AUTHENTICATION.md)                               | Clerk and RBAC                 |

---

_Violations of §3 (layered architecture) should be fixed in refactor, not extended with new code in the wrong layer._
