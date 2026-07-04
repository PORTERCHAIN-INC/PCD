# Merchant Portal — Architecture Audit

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Date:** June 30, 2026  
**Scope:** `apps/merchant-portal/`, `merchant_engine/`, `/v1/merchant/*`, `/v1/merchant-api/*`, Fleetbase sync path  
**Method:** Source-code trace from UI → API → services → adapter → Fleetbase

**Status key:** ✅ Implemented · ⚠ Partial · ❌ Missing · 🚫 Violation

---

## 1. Locked topology compliance

Required flow per masterrule §1 and §7:

```
Merchant Portal (:3001)
    ↓ HTTPS /v1/*
FastAPI Router (Controller)
    ↓
Application Service (merchant_engine/*)
    ↓
Repository → Porterchain PostgreSQL
    ↓ (async logistics)
Event Bus → fleetbase_engine → Fleetbase Adapter → Fleetbase (:8000)
```

| Check                                | Status | Evidence                                                                            |
| ------------------------------------ | ------ | ----------------------------------------------------------------------------------- |
| Portal calls Porterchain API only    | ✅     | `apps/merchant-portal/src/lib/api.ts` → `NEXT_PUBLIC_PORTERCHAIN_API_URL` (`:8001`) |
| No direct Fleetbase HTTP from portal | ✅     | No `:8000`, `FLEETBASE_*`, or Fleetbase SDK in merchant-portal                      |
| Routers delegate to services         | ✅     | `routers/merchant.py` — thin controllers, no business rules                         |
| Business logic in `merchant_engine/` | ✅     | Booking, bulk, billing, orders, profile, team, API keys                             |
| Fleetbase via adapter only           | ✅     | `transition_to_dispatch_ready` → event → `BookingSyncService` → adapter             |
| `fleetbase_order_id` read-only in UI | ✅     | Display field only in `MerchantOrder` type                                          |

**Fleetbase boundary verdict:** ✅ **Compliant** — Merchant Portal never communicates directly with Fleetbase.

---

## 2. Already implemented

### 2.1 Frontend (`apps/merchant-portal/`)

| Feature                                   | Route                               | API                                                   | Status |
| ----------------------------------------- | ----------------------------------- | ----------------------------------------------------- | ------ |
| Clerk authentication                      | `/sign-in`                          | —                                                     | ✅     |
| Dashboard KPIs                            | `/dashboard`                        | `GET /v1/merchant/dashboard`                          | ✅     |
| Single booking + Google Maps autocomplete | `/book`                             | `POST /v1/merchant/bookings`                          | ✅     |
| Bulk CSV upload + confirm                 | `/bulk`                             | `POST /bulk/upload`, `POST /bulk/{id}/confirm`        | ✅     |
| Orders list, search, filter               | `/orders`                           | `GET /v1/merchant/orders`                             | ✅     |
| Order detail + timeline                   | `/orders/[order_id]`                | `GET /orders/{id}`                                    | ✅     |
| Cancel / duplicate order                  | `/orders`                           | `POST /orders/{id}/cancel`, `/duplicate`              | ✅     |
| Track by tracking number                  | `/track`                            | `GET /track/{number}`                                 | ✅     |
| Billing statement + invoices              | `/billing`                          | `GET /billing/statement`, `/billing/invoices`         | ✅     |
| Reports summary                           | `/reports`                          | `GET /reports/summary`                                | ✅     |
| API key create/list/revoke                | `/api`                              | `GET/POST/DELETE /api-keys`                           | ✅     |
| Team invite/remove                        | `/team`                             | `GET /team`, `POST /team/invite`, `DELETE /team/{id}` | ✅     |
| Business profile edit                     | `/settings`                         | `GET/PATCH /profile`                                  | ✅     |
| RBAC via Clerk org headers                | middleware + `MerchantAuthProvider` | `X-Merchant-Org-Id`, `X-Merchant-Role`                | ✅     |
| Dev auth bypass                           | `MerchantAuthProvider`              | `Bearer dev` + `dev_merchant_org`                     | ✅     |

### 2.2 Backend (`merchant_engine/`)

| Service                    | Responsibility                                                | Status |
| -------------------------- | ------------------------------------------------------------- | ------ |
| `MerchantBookingService`   | Net-terms booking, cancel, duplicate; pricing; dispatch-ready | ✅     |
| `MerchantBulkService`      | CSV upload preview + confirm                                  | ✅     |
| `MerchantOrdersService`    | List/search orders, tracking timeline                         | ✅     |
| `MerchantDashboardService` | KPI aggregates                                                | ✅     |
| `MerchantBillingService`   | Statement, outstanding balance, invoice list                  | ✅     |
| `MerchantReportsService`   | Monthly analytics, top routes                                 | ✅     |
| `MerchantProfileService`   | Profile CRUD, saved addresses, recipients                     | ✅     |
| `MerchantTeamService`      | Team invite/remove/role update                                | ✅     |
| `MerchantApiKeyService`    | API keys + webhooks CRUD + audit                              | ✅     |
| `MerchantSyncService`      | Pre-dispatch validation gate (status, contract, terms)        | ✅     |
| RBAC (`rbac.py`)           | Module permissions per `MerchantRole`                         | ✅     |
| Auth (`auth/merchant.py`)  | Clerk JWT + org resolution                                    | ✅     |

### 2.3 Fleetbase integration path

| Stage                     | Component                                                 | Status |
| ------------------------- | --------------------------------------------------------- | ------ |
| Pre-booking validation    | `fleetbase_engine/merchant_sync_service.py`               | ✅     |
| Dispatch-ready transition | `booking_engine/order_transitions.py`                     | ✅     |
| Event emission            | `order.dispatch_ready`                                    | ✅     |
| Event handler             | `booking_engine/fleetbase_sync_handler.py`                | ✅     |
| Outbound sync             | `fleetbase_engine/booking_sync_service.py`                | ✅     |
| Adapter boundary          | `services/fleetbase-adapter/` via `integration_bridge.py` | ✅     |
| Inbound webhooks          | `routers/webhooks.py` → `WebhookProcessor`                | ✅     |
| Tracking UI data source   | Porterchain `OrderEvent` mirror                           | ✅     |

### 2.4 Data model

| Entity                  | Table                        | Status          |
| ----------------------- | ---------------------------- | --------------- |
| Merchant                | `merchants`                  | ✅              |
| MerchantUser            | `merchant_users`             | ✅              |
| SavedAddress            | `saved_addresses`            | ✅              |
| MerchantRecipient       | `merchant_recipients`        | ✅              |
| MerchantApiKey          | `merchant_api_keys`          | ✅              |
| MerchantWebhook         | `merchant_webhooks`          | ✅              |
| BulkImportJob           | `bulk_import_jobs`           | ✅              |
| MerchantAuditLog        | `merchant_audit_logs`        | ✅              |
| MerchantBookingTemplate | `merchant_booking_templates` | ✅ (model only) |

---

## 3. Partially implemented

| Area                             | What exists                                   | Gap                                                                       |
| -------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------- |
| **Programmatic API**             | API keys stored; portal UI to create keys     | `/v1/merchant-api` auth router was missing (foundation fix in this audit) |
| **Outbound webhooks**            | CRUD backend; event fanout queued             | No portal UI; worker delivery was stub; signing secret storage incomplete |
| **Saved addresses / recipients** | Backend CRUD on `/addresses`, `/recipients`   | No portal UI; book page does not use saved address IDs                    |
| **Team management**              | Backend role PATCH                            | No role-change UI; invites use `pending_{email}` — no Clerk org sync      |
| **Bulk upload**                  | UI accepts `.xlsx` label                      | Backend parses CSV only                                                   |
| **Billing**                      | Statement + invoice list                      | No NET batch invoice run; `pdf_url` unused                                |
| **Reports**                      | Summary endpoint                              | `average_delivery_minutes` always `null`                                  |
| **Dashboard**                    | KPI cards                                     | `notifications` always empty array                                        |
| **Tracking**                     | Timeline from Porterchain events              | Poll-on-load only; no live map or WebSocket                               |
| **API keys**                     | Create/list/revoke                            | Scopes not exposed in create form (defaults used)                         |
| **Booking templates**            | DB model + schema fields                      | No API or UI                                                              |
| **Cancel → Fleetbase**           | `BookingSyncService.sync_cancellation` called | Direct service call, not event-driven (inconsistent with dispatch path)   |
| **Path alias**                   | `apps/merchant-portal/` active                | `apps/merchant/` remains README placeholder                               |

---

## 4. Missing

| Item                                     | masterrule / docs reference               | Priority        |
| ---------------------------------------- | ----------------------------------------- | --------------- |
| `/v1/merchant-api` programmatic surface  | §5 Merchant portal, `MERCHANT_FLOW.md`    | P1 — foundation |
| Merchant webhook HTTP delivery           | §12 Event bus, `SECURITY.md`              | P1 — foundation |
| Merchant support module                  | RBAC `support` permission, no routes      | P2              |
| Invoice payment flow                     | RBAC `invoices_pay` module, no endpoint   | P2              |
| NET batch billing / invoice generation   | §11.2, `MerchantBillingService` read-only | P2              |
| Booking templates / recurring            | Schema + model, no service                | P3              |
| Live tracking map                        | —                                         | P3              |
| Docker service entry for merchant-portal | Runs via `pnpm dev:merchant` only         | P3              |
| Clerk org invitation sync                | Team invites local DB only                | P3              |

---

## 5. Architecture violations

| ID    | Layer             | Violation                                                                                                                                    | Severity | Location                                     |
| ----- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------- | -------- | -------------------------------------------- |
| AV-01 | Service → Adapter | `MerchantBookingService.cancel_order` calls `BookingSyncService.sync_cancellation()` directly instead of via `order.cancelled` event handler | ⚠ Medium | `merchant_engine/booking_service.py:128-129` |
| AV-02 | Router            | `cancel_order` router fetches order then passes to booking service — acceptable orchestration, but duplicates lookup pattern                 | ⚠ Low    | `routers/merchant.py:236-239`                |
| AV-03 | Data              | `MerchantWebhook.secret_hash` only — HMAC signing at delivery requires reversible secret storage                                             | ⚠ Medium | `merchant_models.py`, `api_key_service.py`   |
| AV-04 | Worker            | `processors/webhooks.py` logs fanout only — event bus path incomplete                                                                        | ⚠ Medium | `apps/worker/processors/webhooks.py`         |

**No violations found:**

- UI → Fleetbase direct calls 🚫
- Business logic in React components 🚫
- Business logic in routers 🚫
- Fleetbase HTTP outside adapter 🚫 (from merchant path)
- Pricing logic in merchant portal UI 🚫

---

## 6. Duplicate components

| Item                                        | Assessment                                                                                            |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `apps/merchant-portal/` vs `apps/merchant/` | ⚠ Path alias duplication — only `merchant-portal` is active; `apps/merchant/` is placeholder per §4.2 |
| `@porterchain/maps` shared package          | ✅ Intentional reuse — not duplicate                                                                  |
| Admin merchant 360 vs Merchant self-service | ✅ Intentional separation — different audiences                                                       |
| `StatCard`, `Button`, `Container`           | ✅ Portal-local UI primitives — appropriate scope                                                     |

**No duplicate merchant-specific map or booking components found.**

---

## 7. Duplicate APIs

| Endpoint pair                                        | Assessment                                                           |
| ---------------------------------------------------- | -------------------------------------------------------------------- |
| `GET /orders/{id}/tracking` vs `GET /track/{number}` | ⚠ Same backend logic, two entry points; frontend uses `/track/` only |
| `/v1/merchant/*` vs `/v1/admin/merchants/*`          | ✅ Intentional — self-service vs staff CRM                           |
| `/v1/merchant/*` vs `/v1/merchant-api/*`             | ✅ Intentional — Clerk session vs API key (foundation added)         |

**No parallel booking or billing implementations found.**

---

## 8. Business logic violations

| Check                             | Status | Notes                                                                      |
| --------------------------------- | ------ | -------------------------------------------------------------------------- |
| Pricing in UI                     | ✅     | Book page submits addresses; server calculates via `get_pricing_service()` |
| Payment verification in UI        | ✅ N/A | Net-terms flow — no Stripe checkout in merchant portal                     |
| Order state transitions in UI     | ✅     | Cancel/duplicate via API only                                              |
| State machine in router           | ✅     | Routers call services only                                                 |
| Browser-only booking state        | ✅     | Orders persisted server-side immediately                                   |
| Contract/pricing rules in adapter | ✅     | `MerchantSyncService` + `pricing_engine` in API                            |

| Minor concern                 | Detail                                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------------------ |
| Client `scheduled_at` default | Book page uses `new Date(scheduledAt \|\| Date.now())` — server still validates; acceptable UX default |

---

## 9. Fleetbase violations

| Rule (masterrule §2, §7, §13)                        | Status                                   |
| ---------------------------------------------------- | ---------------------------------------- |
| Merchant portal must never call Fleetbase            | ✅ Verified                              |
| Fleetbase owns execution only (dispatch, GPS, POD)   | ✅                                       |
| Porterchain owns pricing, billing, merchant accounts | ✅                                       |
| All Fleetbase HTTP via adapter                       | ✅ (outbound path)                       |
| Commercial data not duplicated in Fleetbase          | ✅ `fleetbase_order_id` correlation only |

| Concern                            | Detail                                          | Severity                    |
| ---------------------------------- | ----------------------------------------------- | --------------------------- |
| Direct cancel sync                 | Bypasses event bus for cancellation propagation | ⚠ Medium                    |
| `sync_return/damage/claim` unwired | Exception flows don't sync to Fleetbase         | ⚠ Low (shared platform gap) |

---

## 10. Layer compliance matrix

| Layer               | Location                                             | Merchant compliance                                 |
| ------------------- | ---------------------------------------------------- | --------------------------------------------------- |
| UI                  | `apps/merchant-portal/`                              | ✅ Render + fetch only                              |
| Controller          | `routers/merchant.py`                                | ✅ Thin                                             |
| Application Service | `merchant_engine/`                                   | ✅ Business logic home                              |
| Repository          | `merchant_models.py`, SQLAlchemy queries in services | ✅ Mostly in services (acceptable monolith pattern) |
| Adapter             | `fleetbase_engine/` → `services/fleetbase-adapter/`  | ✅ No merchant-specific adapter bypass              |

---

## 11. Security posture

| Control                                                  | Status                     |
| -------------------------------------------------------- | -------------------------- |
| Clerk JWT on portal routes                               | ✅                         |
| `X-Merchant-Org-Id` org scoping                          | ✅                         |
| RBAC module checks                                       | ✅                         |
| API key SHA-256 storage                                  | ✅                         |
| API key auth router                                      | ❌ → ✅ (foundation fix)   |
| Webhook HMAC signing                                     | ⚠ Partial (foundation fix) |
| Dev bypass gated on `clerk_dev_bypass` / `app_env=local` | ✅                         |

---

## 12. Observability

| Item                                                  | Status           |
| ----------------------------------------------------- | ---------------- |
| Domain events on booking (`merchant.booking_created`) | ✅               |
| API key audit log                                     | ✅               |
| Fleetbase sync audit + retry queue                    | ✅               |
| Merchant portal-specific metrics                      | ⚠ None dedicated |
| Correlation IDs via `RequestIdMiddleware`             | ✅               |

---

## 13. Compliance score

| Dimension            | Score  | Notes                                            |
| -------------------- | ------ | ------------------------------------------------ |
| Locked topology      | 95/100 | Cancel sync path inconsistent                    |
| Layered architecture | 92/100 | Routers clean; one direct adapter call on cancel |
| Fleetbase boundary   | 98/100 | No portal violations                             |
| Feature completeness | 78/100 | Core flows live; secondary features partial      |
| API design           | 85/100 | `/v1/merchant-api` was missing                   |
| Security             | 80/100 | API key auth + webhook delivery gaps             |

**Overall merchant surface: 88/100** — architecturally sound; foundation gaps addressed in this audit cycle.

---

## 14. Related documents

| Document                                                                   | Purpose                    |
| -------------------------------------------------------------------------- | -------------------------- |
| [MERCHANT_GAP_ANALYSIS.md](./MERCHANT_GAP_ANALYSIS.md)                     | Prioritized remediation    |
| [MERCHANT_COMPONENT_MATRIX.md](./MERCHANT_COMPONENT_MATRIX.md)             | UI ↔ API ↔ Service mapping |
| [masterrule.md](./masterrule.md)                                           | Source of truth            |
| [docs/architecture/MERCHANT_FLOW.md](./docs/architecture/MERCHANT_FLOW.md) | Flow diagram               |
| [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md)     | Platform-wide alignment    |

---

_Audit performed per masterrule §19 — search existing code before creating new modules; preserve locked topology._
