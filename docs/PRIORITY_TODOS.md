# Priority TODOs — Porterchain

**Type:** CANONICAL  
**masterrule:** [Appendix D](../masterrule.md#appendix-d--phase-alignment-checklist-zero-complexity)  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-06  
**Progress:** 63/408 checklist items (~15%) · **P0 code: DD-01–DD-08 complete**

Track execution here. Check boxes when done; add date + commit SHA in **Done** column.

---

## Next up (in order)

| #     | ID          | Task                                                 | Status                                     |
| ----- | ----------- | ---------------------------------------------------- | ------------------------------------------ |
| **1** | **§0.4.10** | Manual Clerk login all 4 portals (+ mobile EAS keys) | Portals return 200; sign-in not documented |
| 2     | —           | Prod ops: `clerk_mode: enterprise`, Valhalla tiles   | API recreate after Doppler sync            |
| 4     | DD-05b      | Fleetbase prod                                       | Blocked on host + secrets                  |
| 5     | DD-09a      | Split `crm_service.py`                               | First P1 code item                         |

---

## Firebase mobile credentials (verified 2026-07-05)

| File                                                     | Bundle / package                                             | Project             | Status          |
| -------------------------------------------------------- | ------------------------------------------------------------ | ------------------- | --------------- |
| `GoogleService-Info_cust.plist`                          | `com.porterchain.customer` (iOS)                             | `porterchain-55313` | ✅ Customer app |
| `GoogleService-Info (1).plist`                           | `com.porterchain.PCD` (iOS)                                  | `porterchain-55313` | ✅ Driver app   |
| `google-services_cust.json` / `google-services (1).json` | `com.porterchain.PCD` + `com.porterchain.customer` (Android) | `porterchain-55313` | ✅ Both apps    |

**§0.1.3:** Prod push test sent 2026-07-06 — 2/4 devices (both iOS) via `send_test_push.py`; web tokens stale. **Confirm notification on physical iPhone.**

---

## Remaining required (P0 ops — not code)

| Priority | ID      | Action                                                              | How to verify                                         |
| -------- | ------- | ------------------------------------------------------------------- | ----------------------------------------------------- |
| 1        | §0.4.10 | **Clerk login walkthrough** — admin, merchant, customer, driver web | Sign-in + API access gate per portal                  |
| 2        | DD-05b  | **Fleetbase prod** — host Fleetbase, set secrets, enable bridge     | `fleetbase_sync.meets_slo: true`                      |
| 3        | DD-02   | **Sentry DSN** — optional                                           | `gh secret set SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` |

**GitHub / Doppler gaps:** `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, all `FLEETBASE_*`. `DOPPLER_TOKEN` ✅ set.

```bash
pnpm validate:p0:prod
curl -fsS https://api.porterchain.com/health/ready | jq '.checks, .clerk_mode, .clerk_apps'
bash scripts/verify-clerk.sh   # on droplet
```

---

## This week (start here — 5 items)

- [x] **DD-06** Rate limit fail-closed + pooled Redis — _(2026-07-05)_
- [x] **DD-12** `jwt_secret` boot fails if dev default in prod — _(2026-07-05)_
- [x] **DD-04** `pcd-worker` in prod compose — _(2026-07-05)_
- [x] **DD-02** Sentry on API + portals — _(2026-07-05)_
- [x] **DD-01** Order state machine tests — _(2026-07-05)_

---

## P0 — Critical (Wave DD)

| Done | ID       | Task                                            | Effort                                            | Notes                                                     |
| ---- | -------- | ----------------------------------------------- | ------------------------------------------------- | --------------------------------------------------------- |
| [x]  | DD-06    | Rate limit fail-closed + pooled Redis           | 1 day                                             |                                                           |
| [x]  | DD-12    | `jwt_secret` boot fails if dev default          | 0.5 day                                           |                                                           |
| [x]  | DD-04    | Worker in prod compose + queue health           | 1–2 days                                          | Worker needs Clerk env + Firebase JSON fix _(2026-07-06)_ |
| [x]  | DD-02    | Sentry + OpenTelemetry on API (then portals)    | 2 days                                            | OTel needs `OTEL_EXPORTER_OTLP_ENDPOINT`                  |
| [x]  | DD-10    | CI security: Dependabot + CodeQL + Trivy        | 0.5 day                                           |                                                           |
| [x]  | DD-01a–d | API tests + booking + Stripe idempotency        | —                                                 |                                                           |
| [x]  | DD-05a   | Dispatch worker (not stub)                      | 2 days                                            |                                                           |
| [x]  | §0.1.3   | `PORTERCHAIN_PUSH_SEND=true` prod + device test | 2 iOS sent prod _(2026-07-06)_; confirm on device |
| [x]  | §0.1.9   | Stripe live webhook + invoice proof             | 1 day                                             | `INV-20260706-ECA602` _(2026-07-06)_                      |
| [~]  | DD-05b   | Fleetbase prod                                  | 1–2 wks                                           | Blocked on host + secrets                                 |
| [x]  | DD-07–08 | Tenant isolation + payment transactions         | —                                                 |                                                           |

---

## P1 — High

| Done | ID     | Task                                      | Notes                         |
| ---- | ------ | ----------------------------------------- | ----------------------------- |
| [x]  | DD-11  | WebSocket hub → Redis pub/sub             | `224c5ce`                     |
| [x]  | DD-03  | ADR-012 horizontal scale (2 API replicas) | `224c5ce`                     |
| [x]  | DD-17  | k6 load tests + p95 SLO                   | `tests/load/`                 |
| [x]  | DD-14  | Secret manager (Doppler)                  | `pcd` / `prd`                 |
| [x]  | §0.1.6 | Valhalla/OSRM in prod routing path        | Deployed; tiles building      |
| [x]  | §0.5   | Clerk 4 apps + JWKS                       | Doppler + deploy; portals 200 |
| [ ]  | DD-09a | Split `crm_service.py`                    | **Next code** after §0.4.10   |
| [ ]  | DD-09b | Split `diagnostics_service.py`            |                               |
| [ ]  | DD-09c | Split `e2e_validation_service.py`         |                               |
| [ ]  | DD-13  | Fleetbase sync SLO ≥98%                   |                               |
| [ ]  | DD-19  | Managed Postgres + read replica           |                               |
| [ ]  | DD-15  | API versioning + CHANGELOG                |                               |

---

## P2 — Product & platform

| Done | Task                                            | Checklist                                 |
| ---- | ----------------------------------------------- | ----------------------------------------- |
| [ ]  | Remove `BookingWidget` from homepage hero       | §6.2.1                                    |
| [ ]  | Maps on website + customer track pages          | §6.2.3                                    |
| [ ]  | `/platform` page + footer links live            | §1.1.5–7                                  |
| [ ]  | Write `docs/ICP.md`                             | §1.3.1                                    |
| [ ]  | Partner API docs + Postman + CHANGELOG          | §7.1                                      |
| [ ]  | Remove "logistics company" copy                 | §1.1.2                                    |
| [~]  | Manual Clerk login all portals                  | §0.4.10 — portals up; walkthrough pending |
| [x]  | Prod ≡ local env diff table in RUNBOOK          | §0.1.11                                   |
| [ ]  | Playwright smoke: merchant sign-in, book, track | §2.1.9                                    |

---

## P3 — Moat & enterprise (defer)

Shopify app · ETA calibration · vertical workflow · SOC 2 · SAML · NetSuite · `/developers`

---

## Do NOT do yet

CRM UI / Route Center · microservices rewrite · `intelligence_engine` · new portals

---

## Related

| Document                                                                                  | Role              |
| ----------------------------------------------------------------------------------------- | ----------------- |
| [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)          | Full gates        |
| [RUNBOOK.md](../RUNBOOK.md)                                                               | Ops               |
| [infrastructure/deploy/CLERK_APPS_SETUP.md](../infrastructure/deploy/CLERK_APPS_SETUP.md) | Clerk 4-app setup |
