# Porterchain — Architecture Alignment Report

**Original audit:** June 30, 2026  
**Last verified:** 2026-07-04  
**Status:** Historical alignment report + July 2026 status update

> **Canonical topology:** [docs/architecture/SYSTEM_ARCHITECTURE.md](./docs/architecture/SYSTEM_ARCHITECTURE.md) · **Repo layout:** [REPOSITORY_STRUCTURE.md](./REPOSITORY_STRUCTURE.md)

---

## July 2026 alignment summary

The target logical architecture **matches implementation**. Most "engines" remain **modules inside `apps/api/`**, not separate deployable services — by design for the current monolith phase.

| Layer | June 2026 report | July 2026 status |
| ----- | ---------------- | ---------------- |
| Website | ✅ Implemented | ✅ Active `:3000` |
| Customer portal | ⚠️ Website route only | ✅ **`apps/customer/` :3004** (62% readiness) |
| Merchant portal | ✅ Implemented | ✅ Active `:3001` |
| Admin portal | ✅ Implemented | ✅ Active `:3002` (Porterchain Next.js, not Fleetbase Ember) |
| Porterchain API | ✅ Orchestrator | ✅ `:8001` — modular `*_engine/` monolith |
| Event bus | ✅ Implemented | ✅ `services/event-bus/` + `apps/worker/` |
| Fleetbase adapter | ✅ Implemented | ✅ Sole HTTP boundary |
| Fleetbase core | ✅ Docker stack | ✅ `:8000` / console `:4200` |
| Driver mobile | ❌ Placeholder | ✅ **`apps/mobile-driver/`** (72% readiness) |
| Driver web | ⚠️ Partial | ✅ `apps/driver-portal/` :3003 |
| Mobile customer | — | ✅ **`apps/mobile-customer/`** (62% readiness) |
| Billing / Notification | ⚠️ Embedded modules | ⚠️ Still embedded + worker queues (not separate services) |
| Pricing engine | ⚠️ Library + client dual path | ⚠️ `services/pricing-engine/` + website client preview |

**Overall alignment:** ~**90%** functional (up from ~75%) — remaining gaps are production hardening and layer discipline, not missing apps.

---

## Target vs implemented (logical)

```
Frontends (website, customer, merchant, admin, driver, mobile)
    ↓
Porterchain API :8001  ← "Logistics Orchestrator" (logical name)
    ├── booking_engine / merchant_engine / admin_engine
    ├── fleetbase_engine / driver_engine / pricing_engine
    ├── billing + notification (embedded modules)
    ↓
Event Bus → Worker
    ↓
Fleetbase Adapter → Fleetbase Core
```

**Naming note:** Code uses **Porterchain API**, not "Logistics Orchestrator". Fleetbase has its own `/v1/orchestrator/run` — unrelated to Porterchain API.

---

## Remaining structural gaps

1. **Billing & Notification** — embedded in API + worker, not `services/billing-engine` / `services/notification-engine` (acceptable until scale requires extraction)
2. **Dual pricing** — retail website client engine + server `pricing-engine`; converge when ready
3. **Layer discipline** — see open findings in [ARCHITECTURE_AUDIT.md](./ARCHITECTURE_AUDIT.md) (F-02–F-06)
4. **Production readiness** — [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)

---

## What matches well

- Frontends never call Fleetbase directly
- Fleetbase adapter is sole integration boundary
- Porterchain owns commercial data; Fleetbase owns execution
- Event-driven dispatch via event bus + worker
- Clerk-only auth; PostgreSQL 16 for Porterchain data

---

## Evidence index

| Topic | Path |
| ----- | ---- |
| Architecture rules | `masterrule.md` |
| Canonical diagram | `docs/architecture/SYSTEM_ARCHITECTURE.md` |
| Ports | `PORT_CONFIGURATION.md` |
| Module status | `MODULE_SCORECARD.md` |
| Apps | `apps/*`, `website/` |

---

_Full June 2026 layer-by-layer comparison archived in git history. Use canonical docs above for current state._
