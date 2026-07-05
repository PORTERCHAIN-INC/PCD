# Failure Scenarios Report


**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [RUNBOOK.md](RUNBOOK.md) (canonical doc).

**Source:** E2E validation framework — Phase 5 failure scenario matrix  
**Regenerate:** `pnpm validate:e2e:reports`

> **Catalog:** `apps/api/.../e2e_validation_catalog.py` → `FAILURE_SCENARIOS` (26 scenarios)  
> **Service:** `E2EValidationService` · **Admin:** Diagnostics → E2E Validation

---

## Snapshot (2026-07-02 run)

**Overall:** PASS

All 26 catalogued failure scenarios returned **PASS** in the automated framework run — meaning retry/fallback paths, diagnostics hooks, or domain exception handling exist for each case.

| Scenario | Status | Layer | Notes |
| -------- | ------ | ----- | ----- |
| authentication_failed | ✅ | auth | Clerk or `CLERK_DEV_BYPASS` |
| payment_failed | ✅ | operations | `PaymentService` → FAILED + draft state |
| stripe_webhook_failure | ✅ | billing_engine | Requires `STRIPE_WEBHOOK_SECRET` in prod |
| driver_rejects / driver_cancels | ✅ | operations | ExceptionType + ops queue |
| vehicle_breakdown / driver_offline | ✅ | operations | Retry/fallback paths |
| fleetbase_offline / fleetbase_adapter_failure | ✅ | fleetbase_adapter | RetryQueue + sync jobs |
| google_maps_failure | ✅ | integrations | Diagnostics probe |
| osrm_failure / valhalla_failure | ✅ | operations | Haversine fallback in pricing |
| redis_restart / postgresql_restart | ✅ | operations | Health checks + pool pre-ping |
| firebase_failure | ✅ | operations | Push optional locally |
| websocket_failure | ✅ | operations | Live map poll fallback |
| notification_failure | ✅ | notification_engine | Retry + delivery logs |
| customer_cancels / merchant_cancels | ✅ | operations | ExceptionType flows |
| pickup_failed / delivery_failed | ✅ | operations | Claims/ops queue |
| customer_not_home | ✅ | operations | Exception handling |
| otp_failed / signature_failed / photo_upload_failed / pod_failed | ✅ | operations | POD engine + offline executor |

---

## What PASS means

The E2E framework verifies **code paths and diagnostics coverage exist** — not that every scenario was exercised against live Fleetbase, Stripe, or Firebase in the run.

| PASS | Scenario has documented handler, retry queue, or chaos-test hook |
| FAIL | Missing handler — blocker for production certification |
| WARNING | Handler exists but external dependency not configured |

---

## Regenerate

```bash
pnpm validate:e2e              # summary to stdout
pnpm validate:e2e:reports      # writes FAILURE_SCENARIOS_REPORT.md + DATA_CONSISTENCY_REPORT.md
```

Chaos-style probes also available in Admin Diagnostics (`diagnostics_service.py`) for integrations (Google Maps, OSRM, Valhalla, Redis, PostgreSQL).

---

## Related

| Document | Purpose |
| -------- | ------- |
| [DATA_CONSISTENCY_REPORT.md](./DATA_CONSISTENCY_REPORT.md) | Phase 8 cross-surface checks |
| [EXCEPTION_WORKFLOWS.md](./EXCEPTION_WORKFLOWS.md) | Business exception flows |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) | Platform certification |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
