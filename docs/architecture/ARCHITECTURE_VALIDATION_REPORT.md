# Architecture Validation Report


**Type:** REPORT
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) (canonical doc).

**Original audit:** 2026-06-30  
**Method:** Reverse-engineered from source code, validated against [masterrule.md](../../masterrule.md) v3.1  
**Scope:** Full Porterchain monorepo — documentation update only (no code changes in this pass)

> **Production readiness:** Platform is **not production ready** — see [PRODUCTION_READINESS_REPORT.md](../../PRODUCTION_READINESS_REPORT.md) for the canonical gap list.

---

## Compliance Scores (June 2026 baseline)

| Dimension | Score | Summary |
| --------- | ----- | ------- |
| **Architecture Compliance** | **84/100** | Locked topology implemented; layered separation largely correct |
| **MasterRule Compliance** | **79/100** | Core flows match §10 lifecycles; roadmap gaps remain |
| **Fleetbase Integration** | **86/100** | Adapter boundary enforced; event-driven outbound sync works |
| **Service Separation** | **88/100** | Eight `*_engine` packages with clear domains |
| **Business Logic Separation** | **90/100** | Routers delegate; services own state machines |
| **API Design** | **83/100** | Consistent `/v1` prefixes; driver proxy pattern sound |
| **Security** | **74/100** | Clerk JWT + webhook signatures; dev bypass risk |
| **Scalability** | **78/100** | Monolith API + Redis queues; PostgreSQL 16; admin list caps |
| **Maintainability** | **82/100** | Shared packages, event catalog, adapter facade |

**Overall weighted average (baseline): 81/100**

### July 2026 score adjustments

| Change | Impact |
| ------ | ------ |
| ✅ Merchant API (`/v1/merchant-api/*`) + gateway middleware | API Design +4, Security +3 |
| ✅ Event handlers for return/damage/claim sync | Fleetbase Integration +2 |
| ✅ Merchant webhook fan-out delivery (`webhook_delivery_service`) | Maintainability +2 |
| ✅ Portal rate limit middleware (production) | Security +2 |
| ⚠️ Batch billing, invoice PDF, reports worker still open | MasterRule unchanged |

**Revised estimate (July 2026): ~84/100**

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
| ---- | -------- |
| No UI → Fleetbase HTTP | All frontends use `NEXT_PUBLIC_PORTERCHAIN_API_URL` only |
| Fleetbase via adapter | `fleetbase_integration.py` → `FleetbaseAdapter` |
| Google Maps viz only | `@porterchain/maps` / `@porterchain/mobile-maps`; pricing uses `MapsService` |
| Stripe webhook as payment truth | `StripeWebhookService` + signature verify |
| Booking drafts server-persisted | `booking_drafts` table + `BookingDraftService` |
| Event bus for Fleetbase outbound | `order.dispatch_ready` → handler → `BookingSyncService` |
| Admin SSO only for Fleetbase | `POST /v1/auth/sso/fleetbase` — no direct API calls |
| Single WebSocket | `WS /v1/admin/operations/live-map/ws` only |
| Order state machine centralized | `ORDER_TRANSITIONS` in `domain/states.py` |
| PostgreSQL 16 + Alembic | 13 revisions, head `n2o3p4q5r6s7` |

---

## Issues

### ISSUE-001: Merchant API Key Auth — ✅ RESOLVED (2026-07)

| Field | Detail |
| ----- | ------ |
| **Was** | Keys stored but no auth router |
| **Now** | `routers/merchant_api.py` + `gateway_engine/middleware.py` + `auth/merchant_api.py` |
| **Remaining** | `order_source` for API bookings defaults to `MERCHANT` (API tag TODO) |

### ISSUE-002: Merchant Batch Billing / Invoice Run Missing — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `MerchantBillingService` returns statements; no scheduled NET_7/NET_14 invoice generation job |
| **Impact** | Merchant net-terms billing is read-only; `merchant.billed` event rarely emitted |
| **Priority** | **P1 — High** |

### ISSUE-003: Invoice PDF Not Populated — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `Invoice.pdf_url` column exists but is not set during confirmation or billing |
| **Priority** | **P2 — Medium** |

### ISSUE-004: Direct Fleetbase Cancel (Bypasses Event Bus) — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `MerchantOrdersService.cancel_order()` calls `BookingSyncService.sync_cancellation()` directly |
| **Note** | `order.cancelled` event handler exists — merchant path should emit first |
| **Priority** | **P2 — Medium** |

### ISSUE-005: Fleetbase sync_return/damage/claim — ✅ PARTIALLY RESOLVED

| Field | Detail |
| ----- | ------ |
| **Was** | Handlers missing |
| **Now** | `register_default_handlers` wires `order.return_to_sender`, `order.damaged`, `claim.opened` → sync handlers |
| **Remaining** | Verify all state transitions emit these events consistently |

### ISSUE-006: Worker Queues Partially Stubbed — PARTIALLY RESOLVED

| Field | Detail |
| ----- | ------ |
| **Was** | `webhooks` processor minimal |
| **Now** | `deliver_merchant_fanout` with HMAC-signed POST + retry |
| **Still stub** | `dispatch` and `reports` queue processors log only |
| **Priority** | **P2 — Medium** (reports/dispatch) |

### ISSUE-007: Dev Auth Bypass in Production Risk — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `clerk_dev_bypass` accepts `"dev"` token when enabled |
| **Mitigation** | Default `CLERK_DEV_BYPASS=false`; skipped in production if env correct |
| **Priority** | **P1 — High** (misconfiguration risk) |

### ISSUE-008: Duplicate Quote Path on Website — OPEN (documented)

| Field | Detail |
| ----- | ------ |
| **Problem** | Website `POST /api/quote` preview vs `POST /v1/quotes`; `ROUTING_ENGINE` defaults differ (osrm vs valhalla) |
| **Priority** | **P3 — Low** (server re-validates before payment) |

### ISSUE-009: Customer Portal Split Across Apps — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | Retail features in both `website/` and `apps/customer/` |
| **Priority** | **P3 — Low** |

### ISSUE-010: AdminCrmService Unused — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `admin_engine/crm_service.py` unused; routers use `CrmSalesService` |
| **Priority** | **P3 — Low** |

### ISSUE-011: route.optimized Event Never Emitted — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | `DomainEventType.ROUTE_OPTIMIZED` in catalog but no producer |
| **Priority** | **P3 — Low** |

### ISSUE-012: Firebase Push Verification — OPEN

| Field | Detail |
| ----- | ------ |
| **Problem** | Push channel implemented but production Firebase wiring needs deploy verification |
| **Priority** | **P2 — Medium** |

---

## Architecture Violations vs masterrule.md

| Violation | Severity | Status |
| --------- | -------- | ------ |
| Direct Fleetbase calls from UI | Critical | ✅ **None found** |
| Direct Fleetbase calls from routers | Critical | ✅ **None found** |
| Business logic in routers | High | ⚠️ Minor — occasional inline queries |
| Business logic in adapter | High | ✅ **None found** |
| Browser-only booking state | High | ✅ **Drafts persisted server-side** |
| Google Maps for routing/pricing | Medium | ✅ **Valhalla/OSRM used** |
| Missing event bus for dispatch | Medium | ✅ **order.dispatch_ready wired** |
| Missing adapter usage | Critical | ✅ **All Fleetbase HTTP via adapter** |

---

## Missing Components (vs masterrule.md)

| Component | Status (July 2026) |
| --------- | ------------------ |
| Merchant API-key booking endpoint | ✅ `/v1/merchant-api/bookings` |
| Merchant invoice run / batch billing | ❌ Not implemented |
| Invoice PDF generation | ❌ `pdf_url` not set |
| Pre-Clerk email/phone dedicated UI | ⚠️ Clerk + Stripe used instead |
| `apps/website/` migration | ⚠️ Still at repo root `website/` |
| Full `apps/customer/` consolidation | ⚠️ Partial |
| Async reports generation | ❌ Queue stub only |
| Dispatch queue processor | ❌ Log stub only |

---

## Duplicate Logic

| Area | Locations | Risk |
| ---- | --------- | ---- |
| Customer portal | `website/` + `apps/customer/` | Medium |
| Quote estimation | `website/src/lib/quote/` + `QuoteService` | Low — server authoritative |
| Fleetbase sync | deprecated wrapper + `fleetbase_engine/` | Low |
| CRM services | `AdminCrmService` + `CrmSalesService` | Low — one unused |

---

## Diagram Index

| Document | Mermaid | PlantUML |
| -------- | ------- | -------- |
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

This report is derived from source code analysis. To refresh after major architecture changes:

1. Re-map routers → services → adapters and frontend API clients
2. Update Mermaid (`.mmd`) and PlantUML (`.puml`) in `docs/architecture/`
3. Sync flow `.md` files and re-score against `masterrule.md`
4. Cross-check [PRODUCTION_READINESS_REPORT.md](../../PRODUCTION_READINESS_REPORT.md)

**No application code was modified to produce this documentation update.**
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](../../masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](../../CTO_AUDIT_REPORT.md) | Doc vs code audit |
