# Architecture Validation Report

> **Generated:** 2026-06-30  
> **Method:** Reverse-engineered from source code, validated against [masterrule.md](../../masterrule.md) v3.1  
> **Scope:** Full Porterchain codebase — no code modifications

---

## Compliance Scores

| Dimension | Score | Summary |
|-----------|-------|---------|
| **Architecture Compliance** | **84/100** | Locked topology implemented; layered separation largely correct |
| **MasterRule Compliance** | **79/100** | Core flows match §10 lifecycles; several roadmap gaps remain |
| **Fleetbase Integration** | **86/100** | Adapter boundary enforced; event-driven outbound sync works |
| **Service Separation** | **88/100** | Eight `*_engine` packages with clear domains |
| **Business Logic Separation** | **90/100** | Routers delegate; services own state machines |
| **API Design** | **83/100** | Consistent `/v1` prefixes; driver proxy pattern sound |
| **Security** | **74/100** | Clerk JWT + webhook signatures; dev bypasses and missing API-key auth |
| **Scalability** | **78/100** | Monolith API + Redis queues; PostgreSQL standardized; admin list caps at 500 |
| **Maintainability** | **82/100** | Shared packages, event catalog, adapter facade |

**Overall weighted average: 81/100**

---

## Validation Method

1. Mapped all routers → services → adapters from `apps/api/src/porterchain_api/`
2. Traced frontends via `lib/api.ts` in each app
3. Verified Fleetbase calls only through `services/fleetbase-adapter/`
4. Compared order/booking state machines to `domain/states.py`
5. Cross-checked event handlers in `porterchain_event_bus/handlers/__init__.py`
6. Compared findings to masterrule.md §1–§20

Diagrams: [docs/architecture/](./)

---

## Confirmed Compliant

| Rule | Evidence |
|------|----------|
| No UI → Fleetbase HTTP | All frontends use `NEXT_PUBLIC_PORTERCHAIN_API_URL` only |
| Fleetbase via adapter | `fleetbase_integration.py` → `FleetbaseAdapter` |
| Google Maps viz only | `@porterchain/maps` for autocomplete; pricing uses `MapsService` (OSRM/Valhalla) |
| Stripe webhook as payment truth | `StripeWebhookService` + signature verify |
| Booking drafts server-persisted | `booking_drafts` table + `BookingDraftService` |
| Event bus for Fleetbase outbound | `order.dispatch_ready` → handler → `BookingSyncService` |
| Admin SSO only for Fleetbase | `POST /v1/auth/sso/fleetbase` — no direct API calls |
| Single WebSocket | `WS /v1/admin/operations/live-map/ws` only |
| Order state machine centralized | `ORDER_TRANSITIONS` in `domain/states.py` |

---

## Issues

### ISSUE-001: Merchant API Key Auth Not Implemented

| Field | Detail |
|-------|--------|
| **Problem** | `MerchantApiKeyService` stores keys but no `/v1/merchant-api` or API-key auth router exists |
| **Impact** | B2B API integration path from masterrule.md §5 cannot be used; keys are dead code |
| **Recommended Fix** | Add `routers/merchant_api.py` with `X-Api-Key` auth delegating to `MerchantBookingService` |
| **Priority** | **P1 — High** |

### ISSUE-002: Merchant Batch Billing / Invoice Run Missing

| Field | Detail |
|-------|--------|
| **Problem** | `MerchantBillingService` returns statements; no scheduled NET_7/NET_14 invoice generation job |
| **Impact** | Merchant net-terms billing is read-only; `merchant.billed` event never emitted |
| **Recommended Fix** | Implement billing queue job in `billing_engine` + cron/worker trigger per `billing_cycle` |
| **Priority** | **P1 — High** |

### ISSUE-003: Invoice PDF Not Populated

| Field | Detail |
|-------|--------|
| **Problem** | `Invoice.pdf_url` column exists but is not set during confirmation or billing |
| **Impact** | Customer/merchant cannot download invoice PDFs |
| **Recommended Fix** | Generate PDF in `billing_engine` or document service; set `pdf_url` on invoice creation |
| **Priority** | **P2 — Medium** |

### ISSUE-004: Direct Fleetbase Cancel (Bypasses Event Bus)

| Field | Detail |
|-------|--------|
| **Problem** | `MerchantOrdersService.cancel_order()` calls `BookingSyncService.sync_cancellation()` directly, not via event |
| **Impact** | Inconsistent async pattern; harder to audit and extend (notifications, webhooks) |
| **Recommended Fix** | Emit `order.cancelled` → event handler → `sync_cancellation()` |
| **Priority** | **P2 — Medium** |

### ISSUE-005: Fleetbase sync_return/damage/claim Not Wired

| Field | Detail |
|-------|--------|
| **Problem** | `BookingSyncService.sync_return()`, `sync_damage()`, `sync_claim()` exist but have no callers |
| **Impact** | Exception flows (RETURN_TO_SENDER, DAMAGED, CLAIM_OPEN) don't sync back to Fleetbase |
| **Recommended Fix** | Subscribe handlers to relevant `order.*` events or call from `WebhookProcessor` inverse path |
| **Priority** | **P2 — Medium** |

### ISSUE-006: Worker Queues Partially Stubbed

| Field | Detail |
|-------|--------|
| **Problem** | `dispatch` and `reports` queue processors log only; `webhooks` processor is minimal stub |
| **Impact** | Merchant outbound webhook fanout queued but not reliably delivered |
| **Recommended Fix** | Implement `webhooks.py` processor with HMAC-signed POST to `MerchantWebhook` URLs |
| **Priority** | **P2 — Medium** |

### ISSUE-007: Dev Auth Bypass in Production Risk

| Field | Detail |
|-------|--------|
| **Problem** | `auth/clerk.py` accepts `token=="dev"` when `clerk_dev_bypass` enabled; merchant/admin providers send `"dev"` token |
| **Impact** | Misconfigured production could allow unauthenticated access |
| **Recommended Fix** | Hard-fail if `clerk_dev_bypass` true when `ENV=production`; remove `"dev"` token in prod builds |
| **Priority** | **P1 — High** |

### ISSUE-008: Duplicate Quote Path on Website

| Field | Detail |
|-------|--------|
| **Problem** | Website has local `POST /api/quote` (OSRM/geocode preview) separate from `POST /v1/quotes` |
| **Impact** | Potential price divergence between preview and server quote (masterrule §11.1 allows estimation but requires server validation) |
| **Recommended Fix** | Document clearly; consider deprecating local preview or aligning tariff engine |
| **Priority** | **P3 — Low** (server re-validates before payment) |

### ISSUE-009: Customer Portal Split Across Apps

| Field | Detail |
|-------|--------|
| **Problem** | Retail customer features exist in both `website/.../portal/customer` and `apps/customer/` |
| **Impact** | Duplicate maintenance; masterrule §4.2 notes migration planned |
| **Recommended Fix** | Consolidate to `apps/customer/` per repository structure target |
| **Priority** | **P3 — Low** |

### ISSUE-010: AdminCrmService Unused

| Field | Detail |
|-------|--------|
| **Problem** | `admin_engine/crm_service.py` (`AdminCrmService`) defined but routers use `CrmSalesService` only |
| **Impact** | Dead code; potential confusion |
| **Recommended Fix** | Remove or merge into `CrmSalesService` |
| **Priority** | **P3 — Low** |

### ISSUE-011: route.optimized Event Never Emitted

| Field | Detail |
|-------|--------|
| **Problem** | `DomainEventType.ROUTE_OPTIMIZED` in catalog but no producer in codebase |
| **Impact** | Valhalla optimization path incomplete vs masterrule routing narrative |
| **Recommended Fix** | Emit from route planning service when multi-stop optimization is implemented |
| **Priority** | **P3 — Low** |

### ISSUE-012: Missing Firebase Push Verification

| Field | Detail |
|-------|--------|
| **Problem** | Push queue and `Firebase` referenced in architecture; driver push delivery path exists in driver-platform but notification push channel lightly implemented |
| **Impact** | Push notifications may not deliver in production without full Firebase wiring |
| **Recommended Fix** | Verify `porterchain_services` notification push adapter + env vars in deploy |
| **Priority** | **P2 — Medium** |

---

## Architecture Violations vs masterrule.md

| Violation | Severity | Status |
|-----------|----------|--------|
| Direct Fleetbase calls from UI | Critical | ✅ **None found** |
| Direct Fleetbase calls from routers | Critical | ✅ **None found** |
| Business logic in routers | High | ⚠️ Minor — most routers clean; occasional inline queries in `orders.py` |
| Business logic in adapter | High | ✅ **None found** |
| Browser-only booking state | High | ✅ **Drafts persisted server-side** |
| Google Maps for routing/pricing | Medium | ✅ **OSRM/Valhalla used** |
| Missing event bus for dispatch | Medium | ✅ **order.dispatch_ready wired** |
| Missing adapter usage | Critical | ✅ **All Fleetbase HTTP via adapter** |

---

## Missing Components (vs masterrule.md)

| Component | masterrule Reference | Implementation Status |
|-----------|---------------------|----------------------|
| Merchant API-key booking endpoint | §5.1 Merchant portal | ❌ Not implemented |
| Merchant invoice run / batch billing | §11 Billing | ❌ Not implemented |
| Invoice PDF generation | §10.1 lifecycle | ❌ `pdf_url` not set |
| Pre-Clerk email/phone dedicated UI | §10.1 | ⚠️ Clerk + Stripe used instead |
| `apps/website/` migration | §4.2 | ⚠️ Still at repo root `website/` |
| Full `apps/customer/` consolidation | §5.1 | ⚠️ Partial — split with website |
| Async reports generation | §6.2 worker | ❌ Queue stub only |
| Dispatch queue processor | §6.2 worker | ❌ Log stub only |

---

## Duplicate Logic

| Area | Locations | Risk |
|------|-----------|------|
| Customer portal | `website/portal/customer` + `apps/customer/` | Medium — divergent feature sets |
| Quote estimation | `website/src/lib/quote/` + `QuoteService` | Low — server is authoritative |
| Fleetbase sync | `booking_engine/fleetbase_sync_service.py` (deprecated) + `fleetbase_engine/` | Low — deprecated wrapper exists |
| CRM services | `AdminCrmService` + `CrmSalesService` | Low — one unused |

---

## Incorrect Communication Patterns

| Pattern | Finding |
|---------|---------|
| UI → Fleetbase | ✅ Not present |
| Router → Fleetbase HTTP | ✅ Not present |
| Service → Fleetbase without adapter | ✅ Not present |
| Cancel without event bus | ⚠️ Merchant cancel is direct service call (ISSUE-004) |
| Payment confirmation without webhook | ✅ Mock only in dev (`allow_stripe_mock`) |

---

## Diagram Index

| Document | Mermaid | PlantUML |
|----------|---------|----------|
| System Architecture | [mermaid/system_architecture.mmd](./mermaid/system_architecture.mmd) | [plantuml/system_architecture.puml](./plantuml/system_architecture.puml) |
| Application Flow | [mermaid/application_flow.mmd](./mermaid/application_flow.mmd) | [plantuml/application_flow.puml](./plantuml/application_flow.puml) |
| Booking Flow | [mermaid/booking_flow.mmd](./mermaid/booking_flow.mmd) | [plantuml/booking_flow.puml](./plantuml/booking_flow.puml) |
| Merchant Flow | [mermaid/merchant_flow.mmd](./mermaid/merchant_flow.mmd) | [plantuml/merchant_flow.puml](./plantuml/merchant_flow.puml) |
| Order Lifecycle | [mermaid/order_lifecycle.mmd](./mermaid/order_lifecycle.mmd) | [plantuml/order_lifecycle.puml](./plantuml/order_lifecycle.puml) |
| Dispatch Flow | [mermaid/dispatch_flow.mmd](./mermaid/dispatch_flow.mmd) | [plantuml/dispatch_flow.puml](./plantuml/dispatch_flow.puml) |
| Payment Flow | [mermaid/payment_flow.mmd](./mermaid/payment_flow.mmd) | [plantuml/payment_flow.puml](./plantuml/payment_flow.puml) |
| Event Bus Flow | [mermaid/event_bus_flow.mmd](./mermaid/event_bus_flow.mmd) | [plantuml/event_bus_flow.puml](./plantuml/event_bus_flow.puml) |
| Module Dependency | [mermaid/module_dependency.mmd](./mermaid/module_dependency.mmd) | [plantuml/module_dependency.puml](./plantuml/module_dependency.puml) |
| API Dependency | [mermaid/api_dependency.mmd](./mermaid/api_dependency.mmd) | [plantuml/api_dependency.puml](./plantuml/api_dependency.puml) |
| Database Relationship | [mermaid/database_relationship.mmd](./mermaid/database_relationship.mmd) | [plantuml/database_relationship.puml](./plantuml/database_relationship.puml) |
| Google Maps Flow | [mermaid/google_maps_flow.mmd](./mermaid/google_maps_flow.mmd) | [plantuml/google_maps_flow.puml](./plantuml/google_maps_flow.puml) |
| OSRM Flow | [mermaid/osrm_flow.mmd](./mermaid/osrm_flow.mmd) | [plantuml/osrm_flow.puml](./plantuml/osrm_flow.puml) |
| Valhalla Flow | [mermaid/valhalla_flow.mmd](./mermaid/valhalla_flow.mmd) | [plantuml/valhalla_flow.puml](./plantuml/valhalla_flow.puml) |
| Fleetbase Flow | [mermaid/fleetbase_flow.mmd](./mermaid/fleetbase_flow.mmd) | [plantuml/fleetbase_flow.puml](./plantuml/fleetbase_flow.puml) |
| Notification Flow | [mermaid/notification_flow.mmd](./mermaid/notification_flow.mmd) | [plantuml/notification_flow.puml](./plantuml/notification_flow.puml) |
| Authentication Flow | [mermaid/authentication_flow.mmd](./mermaid/authentication_flow.mmd) | [plantuml/authentication_flow.puml](./plantuml/authentication_flow.puml) |
| Realtime Flow | [mermaid/realtime_flow.mmd](./mermaid/realtime_flow.mmd) | [plantuml/realtime_flow.puml](./plantuml/realtime_flow.puml) |
| Reporting Flow | [mermaid/reporting_flow.mmd](./mermaid/reporting_flow.mmd) | [plantuml/reporting_flow.puml](./plantuml/reporting_flow.puml) |
| Admin Control Tower | [mermaid/admin_control_tower.mmd](./mermaid/admin_control_tower.mmd) | [plantuml/admin_control_tower.puml](./plantuml/admin_control_tower.puml) |

---

## Regeneration

This documentation is derived from source code. To regenerate after architecture changes:

1. Re-run codebase analysis against routers, `*_engine` services, models, adapters, and frontends
2. Update Mermaid (`.mmd`) and PlantUML (`.puml`) sources in `mermaid/` and `plantuml/`
3. Sync embedded diagrams in each `.md` file
4. Re-score against `masterrule.md`

**No application code was modified to produce this report.**
