# Data Consistency Report

**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [DATABASE_ARCHITECTURE.md](DATABASE_ARCHITECTURE.md) (canonical doc).

**Source:** E2E validation framework — Phase 8 consistency checks  
**Regenerate:** `pnpm validate:e2e:reports` (writes repo-root markdown)

> **Catalog:** `apps/api/.../e2e_validation_catalog.py` → `CONSISTENCY_SURFACES`  
> **Service:** `E2EValidationService` · **Architecture:** [DATABASE_ARCHITECTURE.md](./DATABASE_ARCHITECTURE.md)

---

## Snapshot (2026-07-02 run)

**Overall:** WARNING · **Synchronized:** True

| Surface            | Status     | Notes                                                                                                     |
| ------------------ | ---------- | --------------------------------------------------------------------------------------------------------- |
| website_status     | ✅ PASS    | OK                                                                                                        |
| customer_dashboard | ✅ PASS    | OK                                                                                                        |
| merchant_dashboard | ✅ PASS    | OK                                                                                                        |
| admin_orders       | ✅ PASS    | OK                                                                                                        |
| operations_queue   | ✅ PASS    | OK                                                                                                        |
| route_center       | ✅ PASS    | OK                                                                                                        |
| fleetbase          | ⚠️ WARNING | Fleetbase order ID pending sync — expected when `FLEETBASE_DISPATCH_BRIDGE=false` or Fleetbase stack down |
| driver_app         | ✅ PASS    | OK                                                                                                        |
| reports            | ✅ PASS    | OK                                                                                                        |
| billing            | ✅ PASS    | OK                                                                                                        |
| finance            | ✅ PASS    | OK                                                                                                        |
| claims             | ✅ PASS    | OK                                                                                                        |
| notifications      | ✅ PASS    | Order has no retail customer (merchant/E2E flow)                                                          |

---

## Interpretation

| Result      | Meaning                                                                                                     |
| ----------- | ----------------------------------------------------------------------------------------------------------- |
| **PASS**    | Porterchain PostgreSQL mirrors agree across admin/merchant/customer surfaces for test orders                |
| **WARNING** | Non-blocking — often Fleetbase bridge disabled, missing retail customer on merchant-only order, or sync lag |
| **FAIL**    | Cross-surface data mismatch — investigate order mirror vs portal APIs                                       |

Consistency checks **do not** query Fleetbase MySQL directly — they validate Porterchain API responses and mirror fields (`fleetbase_order_id`, state, amounts).

---

## When to re-run

- After schema migrations affecting `orders`, `bookings`, or merchant tables
- Before production cutover
- After enabling `FLEETBASE_DISPATCH_BRIDGE` with live Fleetbase stack

```bash
pnpm docker:up && pnpm db:migrate
pnpm validate:e2e              # console summary
pnpm validate:e2e:reports      # refresh this file + FAILURE_SCENARIOS_REPORT.md
```

Admin UI: Diagnostics → E2E Validation (when API running).

---

## Related

| Document                                                           | Purpose                |
| ------------------------------------------------------------------ | ---------------------- |
| [FAILURE_SCENARIOS_REPORT.md](./FAILURE_SCENARIOS_REPORT.md)       | Phase 5 failure matrix |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) | Platform gates         |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
