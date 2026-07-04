# Porterchain — Architecture Alignment Report

**Document version:** 1.0  
**Date:** June 30, 2026  
**Scope:** Compare the target Porterchain architecture diagram against the current PCD monorepo implementation.

---

## Executive summary

The PCD repository **implements the spirit and most layers** of the target architecture: Next.js frontends, a central FastAPI hub, a pricing package, event bus, Fleetbase adapter, and Docker-hosted Fleetbase core. The main divergences are **packaging and naming**, not direction:

| Area | Target diagram | Current reality | Match |
|------|----------------|-----------------|-------|
| Website | Next.js | `website/` — implemented | ✅ Strong |
| Booking / Customer Portal | Separate layer | Booking in website; customer portal is one route | ⚠️ Partial |
| Merchant Portal | Separate app | `apps/merchant-portal/` — implemented | ✅ Strong |
| Admin Portal (Business) | Separate app | `apps/admin/` — implemented (Porterchain-owned, not Fleetbase Ember) | ✅ Strong |
| Logistics Orchestrator | Named FastAPI service | `apps/api/` — **Porterchain API**, modular `*_engine` packages | ✅ Strong (different name) |
| Pricing Engine | Separate engine | `services/pricing-engine/` library + website client engine | ⚠️ Partial |
| Billing Engine | Separate engine | Embedded in API + Stripe modules + worker queue | ⚠️ Partial |
| Notification Engine | Separate engine | Embedded modules + event bus + worker queues | ⚠️ Partial |
| Event Bus | Central bus | `services/event-bus/` + `apps/worker/` | ✅ Strong |
| Fleetbase Adapter | Adapter layer | `services/fleetbase-adapter/` — enforced by `masterrule.md` | ✅ Strong |
| Fleetbase Core | Dispatch / GPS / POD | Docker stack `apps/fleetbase/` (gitignored vendor) | ✅ Strong |
| Driver Mobile App | Mobile app | `apps/mobile-driver/` placeholder; `apps/driver-portal/` web substitute | ❌ Gap |

**Overall alignment:** ~75% — topology matches; several “engines” are **modules inside the API monolith** rather than separate deployable services.

---

## Target architecture (reference)

```
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
          Logistics Orchestrator (FastAPI)
                      │
      ┌───────────────┼────────────────┐
      │               │                │
      ▼               ▼                ▼
 Pricing         Billing        Notification
 Engine          Engine          Engine

      │               │                │
      └───────────────┼────────────────┘
                      │
                Event Bus
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

---

## As-implemented architecture (June 2026)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND LAYER (Next.js)                            │
├──────────────┬──────────────────┬──────────────┬──────────────────────────┤
│  website/    │ merchant-portal/   │   admin/     │    driver-portal/        │
│  :3000       │ :3001              │   :3002      │    :3003                 │
│              │                    │              │                          │
│ • Marketing  │ • B2B dashboard    │ • CRM        │ • Driver web dashboard   │
│ • Booking    │ • Book / bulk      │ • Orders     │ • Stops / earnings       │
│ • /portal/   │ • Billing          │ • Finance    │                          │
│   customer   │ • API keys         │ • Pricing    │                          │
│ • Tracking   │                    │ • SSO → FB   │                          │
│              │                    │   console    │                          │
└──────┬───────┴─────────┬──────────┴──────┬───────┴────────────┬─────────────┘
       │                 │                 │                    │
       └─────────────────┴─────────────────┴────────────────────┘
                                    │
                         HTTPS only — never Fleetbase direct
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              PORTERCHAIN API  (apps/api)  — port 8001                       │
│              Target name: "Logistics Orchestrator" — not used in code       │
├─────────────────────────────────────────────────────────────────────────────┤
│  booking_engine/     Retail quote → draft → booking → payment → order       │
│  merchant_engine/    B2B bookings, billing queries, bulk, API keys          │
│  admin_engine/       Ops, CRM, finance, drivers, pricing admin, RBAC        │
│  fleetbase_engine/   Outbound sync, inbound webhooks, retry queue           │
│  driver_engine/      Driver auth, Fleetbase bridge                          │
│  pricing_engine/     Factory → services/pricing-engine                      │
├─────────────────────────────────────────────────────────────────────────────┤
│  services/stripe_service.py          Stripe Checkout + webhooks             │
│  booking_engine/notification_*       Notification orchestration (in-process)  │
│  merchant_engine/billing_service.py Merchant billing                        │
│  admin_engine/finance_service.py     Finance / revenue summaries            │
└───────────────┬───────────────────────────────┬─────────────────────────────┘
                │                               │
    ┌───────────┼───────────┐                   │
    ▼           ▼           ▼                   ▼
 pricing-    event-bus   driver-platform   porterchain_services/
 engine      (Redis)     (porterchain_     (stripe, notifications,
 (library)               driver)            maps, dispatch, …)
                │
                ▼
         apps/worker/  — consumes bus + queues
         (emails, sms, push, billing)

                │
                ▼
    services/fleetbase-adapter/  — sole Fleetbase HTTP boundary
                │
                ▼
    apps/fleetbase/ (Docker, gitignored)  — :8000 API, :4200 console
    Dispatch · Driver · GPS · Routes · Tracking · POD

                │
                ▼
    apps/mobile-driver/  — NOT BUILT (README placeholder)
    apps/driver-portal/  — current driver client (web)
```

**Communication rule (enforced):** All frontends → Porterchain API → Fleetbase Adapter → Fleetbase API. See `masterrule.md` §4–5.

---

## Layer-by-layer comparison

### 1. Website (Next.js)

| | |
|---|---|
| **Target** | Public marketing + booking entry |
| **Current path** | `website/` (not `apps/website/`) |
| **Port** | 3000 |
| **Status** | ✅ **Implemented** — Next.js 16, React 19, Tailwind 4, next-intl |
| **Key files** | `website/package.json`, `website/src/components/sections/BookingWidget.tsx` |
| **API** | `NEXT_PUBLIC_PORTERCHAIN_API_URL` → `http://localhost:8001` |

**Notes:** Local quote preview uses `website/src/app/api/quote/route.ts` + `website/src/lib/pricing/engine.ts` before persisting to API. This is a **dual pricing path** (client + server).

---

### 2. Booking / Customer Portal

| | |
|---|---|
| **Target** | Dedicated booking + customer experience layer |
| **Current — Booking** | ✅ Embedded in website |
| **Current — Customer portal** | ⚠️ **Partial** — single page at `website/src/app/[locale]/portal/customer/page.tsx` |
| **Planned** | `apps/customer/README.md` — "Not yet implemented" |
| **Status** | Booking: implemented. Customer portal: minimal dashboard only |

| Capability | Target | Current |
|------------|--------|---------|
| Instant quote | ✅ | `BookingWidget` + `POST /v1/quotes` |
| Booking draft lifecycle | ✅ | `booking_drafts` table, `BookingDraftService`, `/v1/booking-drafts` |
| Auth + payment | ✅ | Clerk + Stripe via `POST /v1/bookings` |
| Order tracking | ✅ | `/track/[tracking]` + `GET /v1/orders/{tracking}` |
| Full customer portal (history, rebook, support) | ✅ | ❌ Single dashboard page |

**Key files:** `website/src/app/[locale]/book/`, `apps/api/src/porterchain_api/booking_engine/`, `apps/api/src/porterchain_api/booking_draft_models.py`

---

### 3. Merchant Portal

| | |
|---|---|
| **Target** | B2B merchant self-service |
| **Current path** | `apps/merchant-portal/` (placeholder also at `apps/merchant/`) |
| **Port** | 3001 |
| **Status** | ✅ **Implemented** |
| **API** | `/v1/merchant/*` — bookings, orders, billing, bulk, API keys, team |
| **Auth** | Clerk + merchant org context |

**Key files:** `apps/merchant-portal/src/app/(portal)/`, `apps/api/src/porterchain_api/routers/merchant.py`, `apps/api/src/porterchain_api/merchant_engine/`

---

### 4. Admin Portal (Business)

| | |
|---|---|
| **Target** | Porterchain business operations console |
| **Current path** | `apps/admin/` |
| **Port** | 3002 |
| **Status** | ✅ **Implemented** — Porterchain-built Next.js app |
| **Modules** | Dashboard, CRM, merchants, drivers, operations, map, orders, booking drafts, claims, pricing, finance, support, reports, settings |
| **Fleetbase** | SSO link to Fleetbase console (`:4200`) for dispatch/map — **not** embedded Ember app |

**Important:** `TECH_STACK.md` still lists "Admin console — Fleetbase (Ember)" as documented-only; **actual admin is `apps/admin/`**. Fleetbase console remains a separate operational UI.

**Key files:** `apps/admin/src/app/(ops)/`, `apps/api/src/porterchain_api/routers/admin.py`, `apps/api/src/porterchain_api/admin_engine/`

---

### 5. Logistics Orchestrator (FastAPI)

| | |
|---|---|
| **Target name** | Logistics Orchestrator |
| **Current name** | **Porterchain API** (`apps/api/`) |
| **Port** | 8001 |
| **Status** | ✅ **Implemented** — central hub for all business logic |
| **Pattern** | Modular monolith with domain `*_engine` packages |

| Engine package | Responsibility |
|----------------|----------------|
| `booking_engine/` | Retail quote, draft, booking, payment, confirmation, tracking |
| `merchant_engine/` | B2B booking, billing, bulk, dashboard |
| `admin_engine/` | Ops, CRM, finance, pricing admin, RBAC |
| `fleetbase_engine/` | Sync jobs, webhooks, retry, audit |
| `driver_engine/` | Driver platform bridge |
| `pricing_engine/` | Bridge to `services/pricing-engine` |

**Async sidecar:** `apps/worker/` — event bus consumer + Redis task queues.

**Key files:** `apps/api/src/porterchain_api/main.py`, `apps/api/run.py`, `apps/worker/run.py`

**Gap vs diagram:** No service literally named "Logistics Orchestrator." Fleetbase has its own `/v1/orchestrator/run` route optimizer behind the adapter — that is **not** the Porterchain API.

---

### 6. Pricing Engine

| | |
|---|---|
| **Target** | Separate Pricing Engine service |
| **Current** | `services/pricing-engine/` (`porterchain_pricing`) — **Python library**, not HTTP service |
| **API bridge** | `apps/api/src/porterchain_api/pricing_engine/`, `services/pricing.py` |
| **Also** | `website/src/lib/pricing/engine.ts` — client-side retail quotes |
| **Status** | ⚠️ **Partial** — server engine exists; retail UX still uses website client engine |

| Consumer | Pricing source |
|----------|----------------|
| Retail website | Client `website_v1` engine → snapshot sent to API |
| Merchant bookings | Server `porterchain_pricing` |
| Admin simulator | `POST /v1/admin/pricing/simulate` |

---

### 7. Billing Engine

| | |
|---|---|
| **Target** | Separate Billing Engine service |
| **Current** | **No `services/billing-engine/`** — distributed modules |
| **Status** | ⚠️ **Partial — embedded** |

| Concern | Location |
|---------|----------|
| Stripe Checkout | `apps/api/.../services/stripe_service.py` |
| Retail payments | `booking_engine/payment_service.py`, `routers/payments.py`, `routers/webhooks.py` |
| Invoices / receipts | `booking_engine/confirmation_service.py` |
| Merchant billing | `merchant_engine/billing_service.py` |
| Admin finance | `admin_engine/finance_service.py` |
| Async billing jobs | Event bus → worker `billing` queue |

**Gap:** Billing is a **cross-cutting capability** inside the API monolith, not a standalone engine service as the diagram implies.

---

### 8. Notification Engine

| | |
|---|---|
| **Target** | Separate Notification Engine service |
| **Current** | **No `services/notification-engine/`** — embedded + worker |
| **Status** | ⚠️ **Partial — embedded** |

| Concern | Location |
|---------|----------|
| Notification service module | `services/python/porterchain_services/notifications/service.py` |
| Booking notifications | `booking_engine/notification_service.py`, `notification_handler.py` |
| Event-driven delivery | `services/event-bus/.../handlers/__init__.py` |
| Actual send | `apps/worker/` queues: `emails`, `sms`, `push` |

**Gap:** Architecture is event-bus + worker queues, not a named Notification Engine deployable.

---

### 9. Event Bus

| | |
|---|---|
| **Target** | Central Event Bus between engines and Fleetbase |
| **Current** | `services/event-bus/` (`porterchain_event_bus`) |
| **Status** | ✅ **Implemented** |
| **Transport** | Redis Streams (production); in-memory sync fallback (local dev) |
| **Publishers** | All engines via `booking_engine/_core.py` → `platform/bus.py` |
| **Consumers** | `apps/worker/` — Fleetbase sync, notifications, billing, webhooks |

**Key files:** `EVENT_BUS.md`, `services/event-bus/porterchain_event_bus/bus.py`, `services/event-bus/porterchain_event_bus/handlers/__init__.py`

---

### 10. Fleetbase Adapter Layer

| | |
|---|---|
| **Target** | Mandatory adapter between Porterchain and Fleetbase |
| **Current** | `services/fleetbase-adapter/` (`porterchain_fleetbase_adapter`) |
| **Status** | ✅ **Implemented** — matches `masterrule.md` §5 |
| **Factory** | `apps/api/.../services/fleetbase_integration.py` |
| **Deprecated shim** | `services/fleetbase/` re-exports adapter |

**Responsibilities (as implemented):** Auth, order/driver/vehicle mapping, tracking, webhooks, retry, logging.

**Rule:** Frontends and API never call Fleetbase directly — only through adapter.

---

### 11. Fleetbase Core

| | |
|---|---|
| **Target** | Dispatch, driver, GPS, routes, tracking, POD |
| **Current** | `apps/fleetbase/` — Docker Compose stack (gitignored vendor clone) |
| **Status** | ✅ **Operational in dev** (verified v0.7.40 per `SERVICE_STATUS.md`) |
| **Ports** | API `:8000`, Console `:4200`, SocketCluster `:38000` |
| **Install** | `pnpm docker:fleetbase:install` + `pnpm docker:fleetbase:up` |

Porterchain stores canonical order state; Fleetbase mirrors execution. Sync: `ORDER_DISPATCH_READY` → adapter → Fleetbase; inbound webhooks update order state.

**Gap:** Fleetbase source not in git checkout (`.gitignore`); must be installed separately.

---

### 12. Driver Mobile App

| | |
|---|---|
| **Target** | Driver Mobile App (Expo / React Native) |
| **Current mobile** | `apps/mobile-driver/` — **README placeholder only** |
| **Current web substitute** | `apps/driver-portal/` — Next.js, port 3003 |
| **Backend** | `services/driver-platform/`, API `/driver-api/v1/*` |
| **Status** | ❌ **Mobile not built**; web portal partial |

**Key files:** `DRIVER_PLATFORM.md`, `apps/driver-portal/`, `apps/api/src/porterchain_api/routers/driver.py`

---

## Port map (local dev)

| Port | Service | Start command |
|------|---------|---------------|
| 3000 | Website | `pnpm dev:website` |
| 3001 | Merchant portal | `pnpm dev:merchant` |
| 3002 | Admin | `pnpm dev:admin` |
| 3003 | Driver web portal | `pnpm dev:driver` |
| 8001 | Porterchain API | `pnpm dev:api` |
| 8000 | Fleetbase API | `pnpm docker:fleetbase:up` |
| 4200 | Fleetbase console | `pnpm docker:fleetbase:up` |
| 5432 | PostgreSQL | `pnpm docker:up` |
| 6379 | Redis | `pnpm docker:up` |

See `PORT_CONFIGURATION.md` for full reference. Check ports: `pnpm ports`.

---

## Alignment matrix

| Layer | Match | Implementation | Primary gap |
|-------|-------|----------------|-------------|
| Website | ✅ 95% | `website/` | Path not `apps/website/`; dual pricing |
| Booking | ✅ 90% | Website + `booking_engine/` | — |
| Customer portal | ⚠️ 40% | One website route | No `apps/customer/` app |
| Merchant portal | ✅ 95% | `apps/merchant-portal/` | Path naming |
| Admin portal | ✅ 95% | `apps/admin/` | Docs still mention Fleetbase Ember admin |
| Orchestrator (API) | ✅ 90% | `apps/api/` | Different name; monolith not microservices |
| Pricing engine | ⚠️ 70% | Library + client engine | Not separate HTTP service |
| Billing engine | ⚠️ 60% | Embedded modules | Not separate service |
| Notification engine | ⚠️ 65% | Modules + worker | Not separate service |
| Event bus | ✅ 90% | `services/event-bus/` | Redis required for full async |
| Fleetbase adapter | ✅ 95% | `services/fleetbase-adapter/` | — |
| Fleetbase core | ✅ 85% | Docker vendor stack | Gitignored source |
| Driver mobile | ❌ 15% | Placeholder | Expo app not built |

---

## Gaps and recommendations

### Critical gaps

1. **Driver mobile app** — Target shows mobile as the driver client; only `driver-portal` (web) exists. Build `apps/mobile-driver/` (Expo) or update target diagram to show web portal as interim.

2. **Customer portal** — Target implies a full portal layer; current is a single dashboard page inside the website. Either implement `apps/customer/` or fold into website with explicit scope in the diagram.

### Structural gaps (diagram vs packaging)

3. **Billing & Notification as separate engines** — Functionality exists but is **embedded in the API monolith + worker**, not `services/billing-engine` or `services/notification-engine`. Options:
   - **A)** Update target diagram to show "Billing / Notification modules" inside Porterchain API
   - **B)** Extract to standalone services when scale requires it

4. **"Logistics Orchestrator" naming** — Rename in docs to **Porterchain API** or add alias in `SYSTEM_ARCHITECTURE.md` to avoid confusion with Fleetbase's route orchestrator.

5. **Dual pricing** — Retail uses website client engine; merchant/admin use server `pricing-engine`. Converge on server-side pricing for retail when ready.

### Documentation drift

6. **Stale references** — `README.md`, `TECH_STACK.md`, `SYSTEM_ARCHITECTURE.md` understate implemented apps (admin, merchant-portal, API, worker).

7. **Path normalization** — Target `apps/website`, `apps/merchant`, `apps/driver` vs actual `website/`, `apps/merchant-portal/`, `apps/driver-portal/`.

### What already matches well

- ✅ Frontends never call Fleetbase directly
- ✅ Fleetbase adapter is the sole integration boundary
- ✅ Porterchain owns commercial data; Fleetbase owns execution
- ✅ Event-driven dispatch and notifications via event bus + worker
- ✅ Clerk auth across portals; Stripe for retail payments
- ✅ Booking draft lifecycle (server-persisted, session merge, audit)

---

## Evidence index

| Topic | Path |
|-------|------|
| Architecture rules | `masterrule.md` |
| Repo layout | `REPOSITORY_STRUCTURE.md` |
| Ports | `PORT_CONFIGURATION.md` |
| Event bus | `EVENT_BUS.md` |
| Fleetbase integration | `FLEETBASE_INTEGRATION.md` |
| Fleetbase status | `SERVICE_STATUS.md` |
| Driver platform | `DRIVER_PLATFORM.md` |
| Website | `website/` |
| Merchant portal | `apps/merchant-portal/` |
| Admin | `apps/admin/` |
| Driver web | `apps/driver-portal/` |
| Porterchain API | `apps/api/src/porterchain_api/` |
| Worker | `apps/worker/` |
| Pricing engine | `services/pricing-engine/` |
| Event bus package | `services/event-bus/` |
| Fleetbase adapter | `services/fleetbase-adapter/` |
| Shared services | `services/python/porterchain_services/` |
| Driver platform lib | `services/driver-platform/` |
| Customer portal (planned) | `apps/customer/README.md` |
| Mobile driver (planned) | `apps/mobile-driver/README.md` |

---

## Conclusion

The PCD monorepo **follows the target topology**: portals stack on a central FastAPI hub, which delegates pricing to a package, billing/notifications through modules and workers, events through a bus, and logistics execution through the Fleetbase adapter to Fleetbase core.

The diagram is **accurate as a logical architecture** but **optimistic as a physical deployment map** — most "engines" are **modules inside `apps/api`**, not separate services. The largest functional gap is the **driver mobile app**; the largest product gap is a **full customer portal**.

**Recommended next step:** Update the official architecture diagram to label `apps/api` as "Porterchain API (orchestrator)" and show Billing/Notification as internal modules unless/until extracted to standalone services.

---

_Report generated from repository audit, June 30, 2026._
