# Production Readiness Report — Porterchain Platform


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** `masterrule.md` v3.1  
**Auditors:** Enterprise Architecture Review

---

## Overall Status: NOT PRODUCTION READY

The platform **does not** receive Production Ready status. Critical booking workflow defects were fixed during this audit, but remaining High-severity gaps block end-to-end certification.

---

## Certification Criteria

| Criterion                         | Status             | Blocker?                    |
| --------------------------------- | ------------------ | --------------------------- |
| Locked architecture implemented   | ✅ PASS            | No                          |
| No Fleetbase bypass               | ✅ PASS            | No                          |
| Layered architecture              | ⚠️ PARTIAL         | No                          |
| Retail booking E2E (with webhook) | ✅ PASS (post-fix) | No                          |
| Merchant booking E2E              | ✅ PASS            | No                          |
| Dispatch → delivery → POD         | ⚠️ PARTIAL         | **Yes** — Fleetbase runtime |
| Billing / invoicing (retail)      | ✅ PASS            | No                          |
| NET merchant billing              | ⚠️ PARTIAL         | No                          |
| Notifications (all channels)      | ⚠️ PARTIAL         | **Yes** — Firebase prod creds |
| Security hardening                | ⚠️ PARTIAL         | **Yes** — global rate limits  |
| Mobile apps (driver + customer)   | ⚠️ PARTIAL         | No — EAS/Firebase ops gaps    |
| Event bus completeness            | ⚠️ PARTIAL         | No                          |
| PostgreSQL + Redis production     | ⚠️ PARTIAL         | Compose defines them; droplet may be empty until deploy succeeds; worker not in prod compose |

---

## Business Workflow Validation (Phase 8)

| Workflow               | Status    | Notes                                 |
| ---------------------- | --------- | ------------------------------------- |
| Website booking        | ✅        | Requires Stripe webhook in prod       |
| Merchant booking       | ✅        |                                       |
| CSV upload             | ✅        | Bulk import                           |
| Manual booking (admin) | ✅        |                                       |
| Dispatch               | ⚠️        | Requires Fleetbase stack              |
| Delivery lifecycle     | ⚠️        | FB webhooks + driver app              |
| Return                 | ⚠️        | Refund events partial                 |
| Claim                  | ✅        |                                       |
| Billing / invoice      | ✅ Retail | NET partial                           |
| Statement (merchant)   | ⚠️        |                                       |
| Notification           | ⚠️        | Email log-only local; FCM needs creds |

---

## Critical Issues — Resolution Status

| ID     | Issue                               | Status      |
| ------ | ----------------------------------- | ----------- |
| BW-C01 | EXPIRED draft blocks Stripe webhook | **FIXED**   |
| EB-H01 | Fleetbase event mapping gaps        | **FIXED**   |
| EB-H02 | `notification.sent` async channels  | **FIXED**   |
| EB-H03 | Refund events not wired             | **PARTIAL** |

---

## High Issues — Open

| ID     | Issue                               | Layer        | Effort   |
| ------ | ----------------------------------- | ------------ | -------- |
| F-02   | Fat driver router                   | API          | 2–3 days |
| F-12   | Merchant → admin engine coupling    | Architecture | 3–5 days |
| BW-H01 | No expiration/reconciliation worker | Worker       | 1–2 days |
| S-01   | No global API rate limits           | Security     | 1–2 days |
| I-01   | Firebase FCM not configured         | Integration  | 1 day    |

---

## Environment Checklist (Production Deploy)

- [ ] `DATABASE_URL` — PostgreSQL (not SQLite)
- [ ] `REDIS_URL` — required, verified
- [ ] `STRIPE_SECRET` + `STRIPE_WEBHOOK_SECRET` — live keys (code field: `STRIPE_SECRET`, not `STRIPE_SECRET_KEY`)
- [ ] `STRIPE_MOCK=false`
- [ ] `CLERK_DEV_BYPASS=false`
- [ ] Per-portal Clerk keys configured
- [ ] `JWT_SECRET` / `SSO_JWT_SECRET` — non-default
- [ ] `FIREBASE_PROJECT_ID` + service account credentials
- [ ] `FLEETBASE_*` — adapter URL + credentials
- [ ] `GOOGLE_MAPS_API_KEY`
- [ ] `VALHALLA_BASE_URL` (if Route Center optimization required)
- [ ] `apps/worker` running (not included in `docker-compose.prod.yml` as of 2026-07-05 — notifications/billing async delivery requires separate worker deploy)
- [ ] Alembic `upgrade head` including `n2o3p4q5r6s7`
- [ ] Stripe webhook endpoint registered in Dashboard

---

## What Works Today (Local Dev)

| Flow                 | Port | Status                              |
| -------------------- | ---- | ----------------------------------- |
| Website quote + book | 3000 | ✅                                  |
| Stripe test checkout | —    | ✅ (with `stripe listen` locally)   |
| Customer portal      | 3004 | ✅                                  |
| Merchant portal      | 3001 | ✅                                  |
| Admin ops            | 3002 | ✅                                  |
| Driver web portal    | 3003 | ✅                                  |
| Mobile driver        | Expo | ⚠️ 72% — field ops work locally     |
| Mobile customer      | Expo | ⚠️ 62% — core flows work locally    |
| API                  | 8001 | ✅                                  |
| Worker               | —    | ✅ with Redis                       |
| Fleetbase dispatch   | 8000 | ⚠️ requires `pnpm docker:fleetbase:up` |

---

## Path to Production Ready

See `ROADMAP.md` for phased remediation. Minimum bar:

1. Configure production Stripe webhooks + verify booking E2E
2. Deploy Firebase credentials; verify push delivery
3. Add global API rate limiting
4. Verify Fleetbase stack + dispatch E2E in staging
5. Add booking draft reconciliation worker
6. Refactor driver router (can parallelize with staging validation)

**Estimated time to Production Ready:** 2–3 weeks with focused execution.

---

## Audit Deliverables

| Document                  | Status |
| ------------------------- | ------ |
| MODULE_SCORECARD.md       | ✅     |
| DATABASE_ARCHITECTURE.md (archived audits in docs/archive/) | ✅ |
| EVENT_BUS.md (archived audit in docs/archive/) | ✅     |
| FLEETBASE_INTEGRATION.md (archived detail reports in docs/archive/) | ✅ |
| INTEGRATIONS.md (archived integration audit in docs/archive/) | ✅ |
| SECURITY.md (archived security audit in docs/archive/) | ✅ |
| GAP_ANALYSIS.md (archived performance/compliance audits in docs/archive/) | ✅ |
| ROADMAP.md                | ✅     |

---

_Single source of truth: `masterrule.md`_
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
