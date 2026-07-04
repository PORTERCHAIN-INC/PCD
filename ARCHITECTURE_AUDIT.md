# Architecture Audit — Porterchain Platform

**Date:** July 3, 2026  
**Reference:** `masterrule.md` v3.1 (locked topology §1, layered architecture §3)  
**Auditors:** Enterprise Architecture Review (automated + code inspection)

---

## Executive Verdict

| Dimension | Status |
|-----------|--------|
| Locked topology implemented | **PASS** |
| Fleetbase single integration path | **PASS** |
| Layered architecture (5-layer) | **PARTIAL** |
| Cross-engine coupling | **PARTIAL** |
| Production Ready | **NO** — see `PRODUCTION_READINESS_REPORT.md` |

The Porterchain locked architecture is implemented end-to-end. Frontends call Porterchain API (`:8001`) only; Fleetbase HTTP is confined to `services/fleetbase-adapter/`. Gaps are primarily **layer discipline** (fat routers, merchant→admin engine imports) rather than missing components.

---

## Layer Validation

```
Website (Next.js) :3000
    ↓ HTTPS /v1/*
Customer Portal :3004
    ↓
Merchant Portal :3001
    ↓
Admin Portal :3002
    ↓
Porterchain API (FastAPI) :8001  ← Logistics Orchestrator
    ↓
Application Services (*_engine/)
    ↓
Repository → PostgreSQL
    ↓ (async)
Event Bus → Worker
    ↓ (logistics)
Fleetbase Adapter → Fleetbase :8000
    ↓
Driver Mobile / Driver Portal :3003
```

| Layer | Location | Wired | Notes |
|-------|----------|-------|-------|
| UI | `website/`, `apps/*` | ✅ | No Fleetbase HTTP from frontends |
| Controllers | `routers/*.py` | ⚠️ | `driver.py` ~1100 lines violates thin-controller rule |
| Application Services | `*_engine/*_service.py` | ✅ | Business logic home |
| Repositories | `models.py`, `*_models.py`, `repositories/` | ✅ | |
| Adapters | `fleetbase-adapter/`, `stripe_service.py` | ✅ | Factory: `fleetbase_integration.py` |

---

## Findings

### F-01 — Admin Fleetbase API quick-link (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | Dev ergonomics shortcut in admin system links |
| **Affected Layer** | UI (Admin) |
| **Recommended Fix** | Gate `fleetbase-api` link behind `NODE_ENV=development` or remove; keep SSO console link only |
| **Effort** | 1 hour |

**File:** `apps/admin/src/lib/system-links.ts`

---

### F-02 — Fat driver router (High)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Root Cause** | Driver endpoints grew in router instead of `driver_engine/` service |
| **Affected Layer** | Controller |
| **Recommended Fix** | Extract `DriverRouterService`; move `db.commit()` and `DriverFleetbaseBridge` wiring to service |
| **Effort** | 2–3 days |

**File:** `apps/api/src/porterchain_api/routers/driver.py`

---

### F-03 — Merchant engine depends on admin engine (High)

| Field | Value |
|-------|-------|
| **Severity** | High |
| **Root Cause** | `MerchantOrdersService` wraps `AdminOrdersService` for lifecycle reuse |
| **Affected Layer** | Application Services |
| **Recommended Fix** | Extract shared `order_engine/` or `domain/order_lifecycle.py`; both portals depend on shared module |
| **Effort** | 3–5 days |

**Files:** `merchant_engine/orders_service.py`, `admin_engine/orders_service.py`

---

### F-04 — Duplicate Fleetbase bridges (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | Three wrappers: `FleetbaseAdapter`, `FleetbaseIntegrationBridge`, `DriverFleetbaseBridge` |
| **Affected Layer** | Adapter / Application Services |
| **Recommended Fix** | Consolidate HTTP in adapter; domain orchestration in `fleetbase_engine/BookingSyncService` only |
| **Effort** | 2 days |

---

### F-05 — Order state constants in admin engine (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | `DONE_STATES`, `IN_FLIGHT` live in `control_tower_service` but consumed by merchant/reporting |
| **Affected Layer** | Application Services |
| **Recommended Fix** | Move to `domain/states.py` or `domain/order_buckets.py` |
| **Effort** | 4 hours |

---

### F-06 — Router query logic (Medium)

| Field | Value |
|-------|-------|
| **Severity** | Medium |
| **Root Cause** | SQLAlchemy queries in `notifications.py`, `orders.py`, `operations.py`, `admin.py` pricing |
| **Affected Layer** | Controller |
| **Recommended Fix** | Move to respective `*_service.py` methods |
| **Effort** | 1–2 days |

---

## Circular Dependencies

| Cycle | Severity | Mitigation |
|-------|----------|------------|
| `booking_engine` ↔ `fleetbase_engine` | Medium | Lazy imports; runtime coupling remains |
| `booking_engine` ↔ `notification_engine` | Medium | Event bus indirection |
| `merchant_engine` → `admin_engine` | High | Architectural inversion |

No import-time cycle between pricing ↔ billing ↔ notification engines.

---

## Compliance Summary (masterrule §3, §7)

| Rule | Status |
|------|--------|
| UI → API only | ✅ |
| No router → Fleetbase HTTP | ✅ |
| Webhooks delegate to services | ✅ |
| Business logic in `*_engine` | ⚠️ Partial (driver router) |
| Fleetbase adapter mandatory | ✅ |
| Server-side booking state | ✅ |

---

## Implemented During Audit

| Fix | Severity | Status |
|-----|----------|--------|
| EXPIRED draft blocks webhook finalization | Critical | **Fixed** — `domain/states.py`, `booking_draft_service.py` |
| `orders.quote_id` unique constraint | High | **Fixed** — migration `n2o3p4q5r6s7` |
| Fleetbase event → domain event mapping gaps | High | **Fixed** — `fleetbase-adapter/events/__init__.py` |

---

*Next: `BOOKING_WORKFLOW_AUDIT.md`, `MODULE_SCORECARD.md`, `GAP_ANALYSIS.md`, `ROADMAP.md`*
