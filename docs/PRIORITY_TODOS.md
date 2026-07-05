# Priority TODOs — Porterchain

**Type:** CANONICAL  
**masterrule:** [Appendix D](../masterrule.md#appendix-d--phase-alignment-checklist-zero-complexity)  
**Checklist:** [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md)  
**Last verified:** 2026-07-05 (prod `validate:p0:prod` — 6 pass, 0 fail)  
**Progress:** 54/408 checklist items (~13%) · **P0 code: DD-01–DD-08 complete**

Track execution here. Check boxes when done; add date + commit SHA in **Done** column.

---

## Remaining required (P0 ops — not code)

All Wave DD **code** blockers are done. Close these manually:

| Priority | ID     | Action                                                                                   | How to verify                                                                   |
| -------- | ------ | ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| 1        | §0.1.3 | **Device push test** — register FCM token on driver/customer app; trigger notification   | Push received on physical device                                                |
| 2        | §0.1.9 | **Stripe dashboard** — webhook URL `https://porterchain.com/webhooks/stripe` (live mode) | `STRIPE_MOCK=false STRIPE_SECRET=sk_live_… pnpm validate:p0:prod` → G8b pass    |
| 3        | §0.1.9 | **Invoice row proof** — complete one live payment                                        | Droplet SQL on `invoices` (G8c hint in `validate:p0:prod`)                      |
| 4        | DD-05b | **Fleetbase prod** — host Fleetbase, set GitHub secrets, enable bridge                   | `GET /health/ready` → `fleetbase_sync.meets_slo: true`; `pnpm fleetbase:replay` |
| 5        | DD-02  | **Sentry DSN** — optional but recommended                                                | `gh secret set SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN`                           |

**Missing GitHub secrets today:** `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN`, all `FLEETBASE_*` (bridge correctly off until set).

```bash
pnpm validate:p0:prod   # automated prod gates (G1, G8, G9, G2/G3 when bridge off)
curl -fsS https://api.porterchain.com/health/ready | jq .
```

---

## This week (start here — 5 items)

- [x] **DD-06** Rate limit fail-closed + pooled Redis — `rate_limit_middleware.py` _(2026-07-05, `e5308c8`)_
- [x] **DD-12** `jwt_secret` boot fails if dev default in prod — `config.py` _(2026-07-05, `e5308c8`)_
- [x] **DD-04** Add `pcd-worker` to prod compose + queue health — `docker-compose.prod.yml` _(2026-07-05, `e5308c8`)_
- [x] **DD-02** Sentry on API + all Next.js portals — `observability.py`, `packages/config/sentry/` _(2026-07-05, `751122c`)_
- [x] **DD-01** Order state machine tests — `test_order_transitions.py` _(2026-07-05, `e5308c8`)_

---

## P0 — Critical (Wave DD, ~2–6 weeks)

_Closes **DD-G1** / Series A technical blockers. Do in order within P0._

| Done | ID     | Task                                                 | Effort   | Files / checklist                                                                 |
| ---- | ------ | ---------------------------------------------------- | -------- | --------------------------------------------------------------------------------- |
| [x]  | DD-06  | Rate limit fail-closed + pooled Redis                | 1 day    | `rate_limit_middleware.py` · §0.7.6                                               |
| [x]  | DD-12  | `jwt_secret` boot fails if dev default               | 0.5 day  | `config.py` · §11.1.13                                                            |
| [x]  | DD-04  | Worker in prod compose + queue health                | 1–2 days | `docker-compose.prod.yml`, `apps/worker/` · §0.1.4                                |
| [x]  | DD-02  | Sentry + OpenTelemetry on API (then portals)         | 2 days   | API + 5 Next.js portals · §0.7.2, B.13 (OTel needs `OTEL_EXPORTER_OTLP_ENDPOINT`) |
| [x]  | DD-10  | CI security: Dependabot + CodeQL + Trivy             | 0.5 day  | `.github/workflows/` · §2.5.5, B.16                                               |
| [x]  | DD-01a | Order state machine tests                            | 2 days   | `tests/test_order_transitions.py` · §2.1.1                                        |
| [x]  | DD-01b | Booking loop integration test                        | 2 days   | `tests/integration/test_booking_loop.py` · §2.1.2                                 |
| [x]  | DD-01c | Stripe webhook idempotency tests                     | 1 day    | `stripe_webhook_service.py` · §2.1.14                                             |
| [x]  | DD-05a | Implement dispatch worker (not stub)                 | 2 days   | `worker/processors/dispatch.py` · §2.2.7                                          |
| [~]  | §0.1.3 | `PORTERCHAIN_PUSH_SEND=true` prod + device test      | 0.5 day  | **G9 pass** on prod; manual device test remaining                                 |
| [~]  | §0.1.9 | Stripe live webhook + invoice row proof              | 1 day    | **G8 pass** ingress; G8b/G8c need live Stripe key + payment proof                 |
| [~]  | DD-05b | Fleetbase prod: bridge on, webhook secret, sync >95% | 1–2 wks  | Code ready; blocked on prod Fleetbase host + GitHub secrets                       |
| [x]  | DD-08  | Order/payment transactions + `SELECT FOR UPDATE`     | 1 wk     | `confirmation_service.py`, `stripe_webhook_service.py` · §0.7.8                   |
| [x]  | DD-07  | Tenant isolation: context + repos + IDOR tests       | 2 wks    | `models.py`, `*_engine/` · §0.7.7, §2.5.1                                         |
| [x]  | DD-01d | ≥20 API test files + CI blocks on failure            | 2 wks    | `apps/api/tests/`, `ci.yml` · ENG-G1                                              |

**P0 exit criteria:** All DD-01–DD-08 checked · Appendix A prod column green for A.3–A.14 · **DD-G1** green

---

## P1 — High (weeks 7–12, after P0 loop works)

| Done | ID     | Task                                                        | Effort   | Checklist                                         |
| ---- | ------ | ----------------------------------------------------------- | -------- | ------------------------------------------------- |
| [ ]  | DD-11  | WebSocket hub → Redis pub/sub                               | 2–3 days | `notification_engine/realtime.py` · §3.5.1        |
| [ ]  | DD-03  | ADR-012 horizontal scale (managed PG/Redis, 2 API replicas) | 6–10 ew  | `docs/architecture/ADR-012-scaling.md` · §3.4.6   |
| [ ]  | DD-17  | k6 load tests + publish p95 SLO                             | 3 days   | `tests/load/` · §5.4                              |
| [ ]  | DD-14  | Secret manager (replace droplet `.env` secrets)             | 2 days   | infra, RUNBOOK · §5.1.13                          |
| [ ]  | §0.1.6 | Valhalla or OSRM in prod routing path                       | 2 days   | `services/routing.py`, prod compose · §0.1.6      |
| [ ]  | §0.5   | Clerk prod keys all 4 portals + JWKS verified               | 1 day    | `auth/clerk_registry.py` · §0.5.1–6               |
| [ ]  | DD-09a | Split `crm_service.py` (1686 LOC → ≤400/module)             | 1 wk     | `collaboration_engine/crm_service.py` · §2.2.1    |
| [ ]  | DD-09b | Split `diagnostics_service.py` (1645 LOC)                   | 1 wk     | `admin_engine/diagnostics_service.py` · §2.2.2    |
| [ ]  | DD-09c | Split `e2e_validation_service.py` (1619 LOC)                | 3 days   | `admin_engine/e2e_validation_service.py` · §2.2.3 |
| [ ]  | DD-13  | Fleetbase sync SLO ≥98% + alerting                          | 3 days   | `fleetbase_engine/retry_queue.py` · §3.5.5        |
| [ ]  | DD-19  | Managed Postgres + read replica for analytics               | 3–4 days | `DATABASE_ARCHITECTURE.md` · §3.4.7               |
| [ ]  | DD-15  | API versioning policy + CHANGELOG                           | 2 days   | `docs/api/CHANGELOG.md` · §7.1.4                  |

---

## P2 — Product & platform (after prod loop is boring)

| Done | Task                                            | Checklist                                                    |
| ---- | ----------------------------------------------- | ------------------------------------------------------------ |
| [ ]  | Remove `BookingWidget` from homepage hero       | §6.2.1 · `website/src/components/sections/BookingWidget.tsx` |
| [ ]  | Maps on website + customer track pages          | §6.2.3 · `website/.../track/`, `apps/customer/.../track/`    |
| [ ]  | `/platform` page + footer links live            | §1.1.5–7                                                     |
| [ ]  | Write `docs/ICP.md` (vertical, geo, ACV, buyer) | §1.3.1                                                       |
| [ ]  | Partner API docs + Postman + CHANGELOG          | §7.1 · `docs/api/`                                           |
| [ ]  | Remove "logistics company" copy from marketing  | §1.1.2 · `website/messages/corporate-en.json`                |
| [ ]  | Manual Clerk login walkthrough all portals      | §0.4.10                                                      |
| [x]  | Prod ≡ local env diff table in RUNBOOK          | §0.1.11 · `RUNBOOK.md`                                       |
| [ ]  | Playwright smoke: merchant sign-in, book, track | §2.1.9                                                       |

---

## P3 — Moat & enterprise (months 4–12, defer until P0+P1)

| Done | Task                                                      | Checklist |
| ---- | --------------------------------------------------------- | --------- |
| [ ]  | Shopify app (order import + tracking push)                | §7.2.1    |
| [ ]  | ETA calibration v0 (needs ≥10k stop legs)                 | §4.2.2    |
| [ ]  | Pick one vertical workflow (medical OR food OR wholesale) | §8.1      |
| [ ]  | SOC 2 Type I timeline                                     | §11.1.1   |
| [ ]  | SAML via Clerk Enterprise                                 | §11.2.1   |
| [ ]  | NetSuite connector MVP                                    | §7.2.3    |
| [ ]  | Developer portal (`/developers`)                          | §7.1.6    |

---

## Do NOT do yet

| Defer                                | Why                                     |
| ------------------------------------ | --------------------------------------- |
| `intelligence_engine` / AI marketing | No training data until prod volume (§4) |
| CRM UI / Route Center                | Phase 2 — loop not boring (§1.2)        |
| Microservices / rewrite              | Masterrule monolith-first (§21)         |
| New portals or engines               | YAGNI until DD Critical closed          |

---

## Milestones

| Milestone                    | Gate                               | Target score     |
| ---------------------------- | ---------------------------------- | ---------------- |
| Week 1 quick wins done       | DD-06, DD-12, DD-04, DD-02 started | Execution 6+     |
| Wave DD complete             | **DD-G1**, **FND-G5**              | ~6/10 overall    |
| §0 Foundation 100%           | **FND-G1–G5**                      | Execution 8+     |
| ENG gates green              | **ENG-G1–G6**                      | Engineering 9+   |
| Fundable technical diligence | **INV-G5** (zero Critical DD)      | Investor 7+      |
| Full checklist               | **OVR-G0–G12**                     | 10/10 (18–24 mo) |

---

## Related

| Document                                                                         | Role                        |
| -------------------------------------------------------------------------------- | --------------------------- |
| [SILICON_VALLEY_READINESS_CHECKLIST.md](./SILICON_VALLEY_READINESS_CHECKLIST.md) | Full 408-item gates         |
| [masterrule.md](../masterrule.md) Appendix D                                     | Phase 1 alignment           |
| [RUNBOOK.md](../RUNBOOK.md)                                                      | Ops execution               |
| Appendix H in checklist                                                          | DD-01–50 diligence register |
