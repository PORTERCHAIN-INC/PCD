# Silicon Valley Readiness Checklist

**Type:** CANONICAL  
**masterrule:** [§20 Golden rules](../masterrule.md#20-golden-rules) · [§21](../masterrule.md#21-simplification--essential-complexity) · [Appendix D](../masterrule.md#appendix-d--phase-alignment-checklist-zero-complexity)  
**Authority:** Evolve the existing system — never rebuild. Martin Fowler discipline.  
**Version:** 2.2  
**Last verified:** 2026-07-08  
**Baseline audit:** Silicon Valley Readiness Report (July 2026)  
**Due diligence register:** [Appendix H](#appendix-h--series-a-technical-due-diligence-dd-0150) — 50 engineering rejection risks ($20M Series A)

---

## Progress dashboard

_Update after each gate review. Score a dimension only when **all** its gate checkboxes (§x-G\*) are green._

| Section            |   Items |    Done |       % | Gate           |
| ------------------ | ------: | ------: | ------: | -------------- |
| §0 Foundation      |      71 |      64 |     90% | [ ]            |
| §1 Product Vision  |      26 |      24 |     92% | [ ]            |
| §2 Engineering     |      48 |      48 |    100% | [x]            |
| §3 Architecture    |      39 |      39 |    100% | [x]            |
| §4 AI              |      18 |       7 |     39% | [ ]            |
| §5 Execution       |      34 |      34 |    100% | [x]            |
| §6 Design          |      22 |      22 |    100% | [ ]            |
| §7 Platform        |      21 |      12 |     57% | [ ]            |
| §8 Moat            |      21 |       4 |     19% | [ ]            |
| §9 Monopoly        |      12 |       8 |     67% | [ ]            |
| §10 Investor       |      24 |       8 |     33% | [ ]            |
| §11 Enterprise     |      26 |       1 |      4% | [ ]            |
| **Appendices A–H** |      56 |      17 |     30% | cross-cutting  |
| **Total**          | **418** | **289** | **69%** | **OVR 5.6/10** |

---

## How to use this document

1. **Score each dimension** 0–10 using the [Scoring rubric](#scoring-rubric) — only when **every gate checkbox** in that section is checked.
2. **Order matters.** Complete [§0 Foundation](#0-foundation--prerequisite-for-any-1010) before §1–§11.
3. **Validate in CI** where a `Verify:` command exists — do not self-certify from memory.
4. **Update this file** when a gate passes: check the box; add date + commit SHA in **Evidence** column.
5. **Do not add new surfaces** until Phase 1 loop is boring in production ([masterrule §21.4](../masterrule.md#214-phase-1-vs-phase-2-uber-30-for-b2b-logistics)).
6. **Cross-reference:** [Appendix F](#appendix-f--top-100-roadmap-cross-reference) maps items to the prioritized top-100 improvement list.
7. **Series A diligence:** Close all **Critical** items in [Appendix H](#appendix-h--series-a-technical-due-diligence-dd-0150) (DD-01–DD-08) before fundraising technical review.
8. **Execution todos:** Day-to-day priorities in [PRIORITY_TODOS.md](./PRIORITY_TODOS.md) (P0–P3).

### Execution policy (2026-07-08)

**Follow the full checklist for the development layer first.** Production-level items are **deferred** until dev layer is complete — then apply prod configuration in one pass (Doppler, droplet, Fleetbase bridge, prod smoke).

| Phase                     | Scope                                         | Examples                                                                                                        |
| ------------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Dev layer (now)**       | Local + CI + code + docs + test keys          | `pnpm validate:p0`, `validate:d2/d3`, portal builds, service splits, Clerk walkthrough on localhost, TECH_STACK |
| **Prod layer (later)**    | Droplet, Doppler `prd`, live keys, prod smoke | `validate:p0:prod`, `validate:d3:prod`, Fleetbase prod, Alembic on droplet, SSL Labs, push on prod devices      |
| **Frozen — do not touch** | Stripe dev + prod complete                    | No `STRIPE_*` changes, webhook registration, or billing config unless explicit bug fix                          |

Mark prod-only rows **`[—]` deferred** in tracking (not `[x]`). Stripe-related open rows that are already done: leave checked; do not reopen.

| Rule                            | Meaning                                                                  |
| ------------------------------- | ------------------------------------------------------------------------ |
| **Strangler, not rewrite**      | Extract boundaries incrementally; keep production running.               |
| **Bounded context over folder** | `*_engine/` must own writes to its tables; no cross-engine SQL.          |
| **Adapter at the edge**         | Fleetbase, Stripe, FCM — HTTP only through adapters.                     |
| **Thin controllers**            | Routers delegate to one service method; no business logic in `routers/`. |
| **Essential complexity only**   | CRM, Route Center, AI marketing — Phase 2 until loop ships.              |
| **Test the seam**               | Contract tests at engine boundaries, not 100% line coverage theater.     |
| **Monolith first**              | Single FastAPI `:8001` until team + traffic justify extraction.          |
| **Docs follow code**            | OpenAPI `/docs` is route truth; markdown explains why.                   |

### Scoring rubric

|   Score | Meaning (all dimensions)                                               |
| ------: | ---------------------------------------------------------------------- |
| **0–3** | Broken or absent; diligence would fail immediately.                    |
| **4–5** | Works locally; prod gaps; investor would pass.                         |
| **6–7** | Prod loop mostly works; gaps in tests, moat, or enterprise.            |
| **8–9** | Series A-ready in this dimension; minor polish only.                   |
|  **10** | Category-leading; all § gates green; metrics prove it for 2+ quarters. |

---

## Scorecard baseline → target

| Dimension         | Baseline   | Target    | Section                           |
| ----------------- | ---------- | --------- | --------------------------------- |
| Product Vision    | 5/10       | 10/10     | [§1](#1-product-vision-1010)      |
| Engineering       | 7/10       | 10/10     | [§2](#2-engineering-1010)         |
| Architecture      | 7/10       | 10/10     | [§3](#3-architecture-1010)        |
| AI                | 2/10       | 10/10     | [§4](#4-ai-1010)                  |
| Execution         | 6/10       | 10/10     | [§5](#5-execution-1010)           |
| Design            | 6/10       | 10/10     | [§6](#6-design-1010)              |
| Platform          | 3/10       | 10/10     | [§7](#7-platform-1010)            |
| Moat              | 2/10       | 10/10     | [§8](#8-moat-1010)                |
| Monopoly          | 2/10       | 10/10     | [§9](#9-monopoly-1010)            |
| Investor Appeal   | 5/10       | 10/10     | [§10](#10-investor-appeal-1010)   |
| Enterprise Appeal | 4/10       | 10/10     | [§11](#11-enterprise-appeal-1010) |
| **Overall**       | **5.2/10** | **10/10** | §0 + §1–§11 all gates             |

---

## §0 Foundation — prerequisite for any 10/10

> Nothing in §1–§11 counts until §0 is complete in **production**.

### §0.1 Production execution loop

| ID     | Gate                                                           | Files / components                                                                          | Verify                                              | Done           |
| ------ | -------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------------- | -------------- |
| 0.1.1  | API healthy in prod                                            | `infrastructure/deploy/docker-compose.prod.yml`, `apps/api/`                                | `pnpm validate:p0:prod` → G1 PASS                   | [x]            |
| 0.1.2  | Firebase push configured                                       | `deploy.yml`, `secrets/firebase-service-account.json`, `notification_engine/fcm_service.py` | `/health/ready` → `firebase: ok`                    | [x]            |
| 0.1.3  | `PORTERCHAIN_PUSH_SEND=true` in prod (real sends, not dry-run) | `docker-compose.prod.yml`, `porterchain_shared/config/settings.py`                          | Test push received on device                        | [~]            |
| 0.1.4  | Worker in prod compose                                         | `docker-compose.prod.yml`, `apps/worker/`                                                   | `pcd-worker` running; queues drain                  | [x]            |
| 0.1.5  | Fleetbase in prod OR manual-ops mode documented                | `FLEETBASE_DISPATCH_BRIDGE`, RUNBOOK                                                        | Bridge on: FB healthy; off: manual SLA doc          | [x]            |
| 0.1.6  | Valhalla or OSRM in prod routing path                          | `services/routing.py`, prod compose                                                         | Non-haversine ETA for prod addresses                | [x]            |
| 0.1.7  | ≥98% orders `fleetbase_order_id` when bridge on                | `fleetbase_engine/sync_health.py`                                                           | `pnpm validate:p0` G2 + `verify_fleetbase_sync_slo` | [x] 2026-07-08 |
| 0.1.8  | `FIREBASE_WEBHOOK_SECRET` set in prod                          | `webhook_ingress_service.py`, GitHub secrets                                                | Signed POST → 200                                   | [ ]            |
| 0.1.9  | Stripe **live** webhook registered                             | `routers/webhooks.py`, Stripe dashboard                                                     | Live event → invoice row                            | [x]            |
| 0.1.10 | D3 prod smoke — 0 warnings                                     | `verify_d3_prod_smoke.py`                                                                   | `pnpm validate:d3:prod`                             | [x]            |
| 0.1.11 | Prod ≡ local env diff documented                               | `RUNBOOK.md`, `apps/api/env.example`                                                        | Diff table; no surprise defaults                    | [x]            |
| 0.1.12 | Caddy TLS all subdomains                                       | `infrastructure/deploy/Caddyfile`                                                           | SSL Labs A; all portals HTTPS                       | [x]            |
| 0.1.13 | Alembic at head in prod                                        | `deploy.yml` repair_and_migrate                                                             | `alembic current` = `o3p4q5r6s7t8`                  | [ ]            |

### §0.2 CI truth gates

| ID    | Gate                                       | Files                              | Verify                                     | Done |
| ----- | ------------------------------------------ | ---------------------------------- | ------------------------------------------ | ---- |
| 0.2.1 | `validate:d2` in CI                        | `ci.yml`, `verify_d2_contracts.py` | CI green                                   | [x]  |
| 0.2.2 | `validate:d3` + `validate:d3:e2e` in CI    | `verify_d3_matrix.py`              | CI green                                   | [x]  |
| 0.2.3 | API Postgres smoke in CI                   | `tests/test_postgres_smoke.py`     | Job green                                  | [x]  |
| 0.2.4 | Prettier on canonical docs                 | `format:check`                     | CI Website green                           | [x]  |
| 0.2.5 | Deploy after CI success only               | `deploy.yml`                       | workflow_run gate                          | [x]  |
| 0.2.6 | All 6 portal Docker images build in deploy | `deploy.yml`                       | 6 GHCR images pushed                       | [x]  |
| 0.2.7 | TypeScript build all portals in CI         | `ci.yml`                           | website, admin, merchant, driver, customer | [x]  |

### §0.3 Masterrule Golden Rules (§20) — architecture law

| ID     | Rule                                                | Enforcement                               | Done                                                                              |
| ------ | --------------------------------------------------- | ----------------------------------------- | --------------------------------------------------------------------------------- |
| 0.3.1  | Locked topology unchanged without masterrule update | ADR + PR review                           | [x]                                                                               |
| 0.3.2  | No Fleetbase bypass                                 | `rg fleetbase` in apps/ frontends         | [x]                                                                               |
| 0.3.3  | Business logic only in Application Services         | `verify_d2_contracts.py` legacy allowlist | [x] 2026-07-08 · notifications_admin + operations off allowlist (svc owns commit) |
| 0.3.4  | Fleetbase stays upstream-clean                      | No Porterchain rules in `apps/fleetbase/` | [x]                                                                               |
| 0.3.5  | Refactor over rewrite policy documented             | CONTRIBUTING_GUIDE                        | [x]                                                                               |
| 0.3.6  | Modularity within `*_engine`                        | `verify_d2_contracts.py` ≤1000 LOC guard  | [x] 2026-07-08                                                                    |
| 0.3.7  | API backward compatibility policy                   | `docs/api/CHANGELOG.md`                   | [x]                                                                               |
| 0.3.8  | One customer surface                                | D2 validate                               | [x]                                                                               |
| 0.3.9  | Thin routers — no new router logic                  | `verify_d2_contracts.py` ≤350 LOC new     | [x] 2026-07-08                                                                    |
| 0.3.10 | No upward engine imports                            | `verify_d2_contracts.py` extended         | [x]                                                                               |
| 0.3.11 | Docs follow code — no parallel pointer sprawl       | Appendix C complete                       | [x]                                                                               |
| 0.3.12 | Essential complexity only                           | Phase 2 UI hidden                         | [x]                                                                               |

### §0.4 D3 Phase 1 feature matrix (masterrule Appendix D)

**Verify:** `pnpm validate:d3` · `validate:d3:e2e` · `validate:d3:prod`

| ID     | Feature                        | Owner                             | Local | Prod              | Done                                                                                 |
| ------ | ------------------------------ | --------------------------------- | ----- | ----------------- | ------------------------------------------------------------------------------------ |
| 0.4.1  | Merchant dashboard             | `merchant_engine`                 | [x]   | [x]               | [x]                                                                                  |
| 0.4.2  | Driver web + mobile            | `driver_engine`                   | [x]   | portal 200        | [x] mobile-theme shell 2026-07-08                                                    |
| 0.4.3  | Customer web + mobile          | `booking_engine`                  | [x]   | quote+sign-in     | [x] mobile-theme shell 2026-07-08                                                    |
| 0.4.4  | Dispatch                       | `fleetbase_engine` + admin ops    | [x]   | bridge off        | [x] validate:d3 local 2026-07-08                                                     |
| 0.4.5  | Routing Valhalla/OSRM          | `services/routing.py`             | [x]   | deployed          | [~] tiles building                                                                   |
| 0.4.6  | Tracking public API + WS       | `booking_engine`, `operations.py` | [x]   | [x]               | [x]                                                                                  |
| 0.4.7  | POD driver + webhook           | `driver_engine`, Fleetbase        | [x]   | no FB prod        | [x] validate:d3 + contract tests 2026-07-08                                          |
| 0.4.8  | Billing Stripe                 | `billing_engine`                  | [x]   | live webhook      | [~]                                                                                  |
| 0.4.9  | Partner API OpenAPI            | `gateway_engine`, `/docs`         | [x]   | [x]               | [x]                                                                                  |
| 0.4.10 | Manual Clerk login each portal | All portals                       | [x]   | [—] prod deferred | [CLERK_PORTAL_WALKTHROUGH.md](./CLERK_PORTAL_WALKTHROUGH.md) local matrix 2026-07-08 |

### §0.5 Clerk production (4 isolated apps)

| ID    | Gate                             | Files                                    | Done |
| ----- | -------------------------------- | ---------------------------------------- | ---- |
| 0.5.1 | Customer Clerk prod keys in API  | `auth/clerk_registry.py`, deploy secrets | [x]  |
| 0.5.2 | Merchant Clerk prod keys         | same                                     | [x]  |
| 0.5.3 | Admin Clerk prod keys            | same                                     | [x]  |
| 0.5.4 | Driver Clerk prod keys           | same                                     | [x]  |
| 0.5.5 | `CLERK_DEV_BYPASS=false` in prod | `docker-compose.prod.yml`                | [x]  |
| 0.5.6 | JWKS URL per portal verified     | `auth/clerk.py`, `/health/ready`         | [x]  |

### §0.6 CTO open issues — must close

| ID    | Issue                         | Sev | Action                      | Files                                   | Done                                       |
| ----- | ----------------------------- | --- | --------------------------- | --------------------------------------- | ------------------------------------------ |
| 0.6.1 | Worker not in prod            | P1  | Add to compose              | `docker-compose.prod.yml`               | [x]                                        |
| 0.6.2 | Fleetbase prod path           | P1  | Deploy or document manual   | RUNBOOK                                 | [x]                                        |
| 0.6.3 | Webhook secret prod           | P1  | GitHub secret               | `webhook_ingress_service.py`            | [~] RUNBOOK cutover doc 2026-07-08         |
| 0.6.4 | Tracking maps on retail       | P2  | Add Google Maps             | `website/.../track/`, customer track    | [x] TrackRouteMap 2026-07-08               |
| 0.6.5 | Customer Stripe return URLs   | P2  | Portal success URL          | `verify_customer_stripe_return_urls.py` | [x] 2026-07-08 customer channel + prod env |
| 0.6.6 | `route.optimized` event drift | P2  | Emit or remove from catalog | `events/catalog.ts`                     | [x]                                        |
| 0.6.7 | API docs thin vs 447 routes   | P2  | Partner API doc             | `apps/api/README.md`, `docs/api/`       | [x] Postman + OpenAPI export 2026-07-08    |
| 0.6.8 | Model sprawl (9 modules)      | P3  | Strangler split             | §3.2                                    | [x] 2026-07-08                             |
| 0.6.9 | Orphan `services/booking.py`  | P3  | Delete if unused            | grep + delete                           | [x]                                        |

### §0.7 Series A diligence — Critical blockers (DD-01–DD-08)

_Close before $20M Series A technical review. Full register: [Appendix H](#appendix-h--series-a-technical-due-diligence-dd-0150)._

| ID    | DD    | Gate                                       | Primary files                                                | Effort  | Done                                                                 |
| ----- | ----- | ------------------------------------------ | ------------------------------------------------------------ | ------- | -------------------------------------------------------------------- |
| 0.7.1 | DD-01 | ≥20 API test files; CI blocks on failure   | `apps/api/tests/` (27 files), `ci.yml`                       | 8–12 ew | [x]                                                                  |
| 0.7.2 | DD-02 | Sentry + OpenTelemetry in prod             | `platform/observability.py`, all apps                        | 2–3 ew  | [x]                                                                  |
| 0.7.3 | DD-03 | Horizontal scale path (not single droplet) | `ADR-012-scaling.md`, `docker-compose.prod.yml`              | 6–10 ew | [x]                                                                  |
| 0.7.4 | DD-04 | Worker in prod compose                     | `docker-compose.prod.yml`, `apps/worker/`                    | 1–2 ew  | [x]                                                                  |
| 0.7.5 | DD-05 | Dispatch worker + Fleetbase prod loop      | `worker/processors/dispatch.py`, `verify_dispatch_worker.py` | 4–6 ew  | [~] dev processor + tests; prod `FLEETBASE_DISPATCH_BRIDGE` deferred |
| 0.7.6 | DD-06 | Rate limit fail-closed + pooled Redis      | `platform/rate_limit_middleware.py:82-99`                    | 1 ew    | [x]                                                                  |
| 0.7.7 | DD-07 | Tenant isolation enforced (RLS or repos)   | `models.py`, `merchant_models.py`, `*_engine/`               | 6–10 ew | [x]                                                                  |
| 0.7.8 | DD-08 | Order/payment transactions + row locks     | `confirmation_service.py`, `stripe_webhook_service.py`       | 3–5 ew  | [x]                                                                  |

### §0.8 Runtime baseline (Fowler stabilize — 2026-07)

_Pin versions; no floating Docker tags. Policy: `.cursor/rules/dependency-freeze.mdc`._

| ID    | Gate                                        | Files / components                                              | Verify                         | Done |
| ----- | ------------------------------------------- | --------------------------------------------------------------- | ------------------------------ | ---- |
| 0.8.1 | Node **24.18 LTS** + pnpm **11.10**         | `.nvmrc`, `package.json`, web Dockerfiles `node:24.18.0-alpine` | `node -v`, `pnpm -v`           | [x]  |
| 0.8.2 | Python **3.14.6** API + CI + image          | `apps/api/Dockerfile`, `ci.yml`, `security.yml`                 | `.venv` + CI Python version    | [x]  |
| 0.8.3 | Docker images exact tags/digests            | `docker-compose*.yml`, `dependency-freeze.mdc`                  | no `:latest` in compose        | [x]  |
| 0.8.4 | Local data stack: PG 18, Redis 8.8, Mailpit | `infrastructure/docker/docker-compose.yml`                      | `docker ps` service versions   | [x]  |
| 0.8.5 | Fleetbase Redis 4 → Valkey override         | `fleetbase.porterchain.override.yml`                            | `valkey/valkey:8.1.8-alpine`   | [x]  |
| 0.8.6 | Frontend dependency freeze until ~2026-10   | `dependency-freeze.mdc`, `.github/dependabot.yml`               | Next/React/TS ignores in place | [x]  |

### §0 Foundation gate

- [ ] **FND-G1:** §0.1 all items checked (prod execution loop complete)
- [ ] **FND-G2:** §0.4 prod column all green or documented exception
- [ ] **FND-G3:** §0.6 P0–P1 issues closed
- [x] **FND-G4:** §0.3 golden rules enforced in CI where automatable (2026-07-08 — `validate:golden-rules`)
- [ ] **FND-G5:** §0.7 all DD Critical items (DD-01–DD-08) closed — 7/8 done; `verify_dd_critical_blockers.py` (0.7.5 prod bridge [~])

---

## 1. Product Vision (10/10)

**10/10 means:** One sentence positioning, one ICP vertical, one core loop, zero identity crisis.

### 1.1 Positioning & narrative

| ID     | Item                                          | Files                                                    | Evidence                           | Done                                               |
| ------ | --------------------------------------------- | -------------------------------------------------------- | ---------------------------------- | -------------------------------------------------- |
| 1.1.1  | Canonical positioning in masterrule           | `masterrule.md` §2 or §22                                | One paragraph B2B orchestration    | [x] validate:product-vision 2026-07-08             |
| 1.1.2  | Remove courier-operator language              | `website/messages/corporate-en.json`, `business-en.json` | No "logistics company" self-desc   | [x] platform copy 2026-07-08                       |
| 1.1.3  | Homepage hero = platform, not consumer book   | `Hero.tsx`, `page.tsx`                                   | No `BookingWidget` above fold      | [x] corporate.home.hero + platform CTAs 2026-07-08 |
| 1.1.4  | Retail book only on customer portal           | `apps/customer/src/app/book/`                            | Website redirects to `:3004`       | [x] `/book` → customer portal 2026-07-08           |
| 1.1.5  | `/platform` page live                         | `website/src/app/[locale]/platform/`                     | 200 + screenshots                  | [x] 2026-07-08                                     |
| 1.1.6  | `/solutions/{vertical}` live                  | `website/src/app/[locale]/solutions/`                    | ≥1 vertical                        | [x] 4 verticals 2026-07-08                         |
| 1.1.7  | Footer links resolve                          | `corporate-en.json`, routes                              | No 404                             | [x] validate:product-vision-pages 2026-07-08       |
| 1.1.8  | Glossary: booking vs order post-payment       | `BUSINESS_GLOSSARY.md`, UI copy                          | Consistent labels                  | [x] validate:product-vision 2026-07-08             |
| 1.1.9  | Billion-dollar stage declared (current stage) | `docs/ICP.md`                                            | Courier → Software → AI → Platform | [x] ICP stage doc 2026-07-08                       |
| 1.1.10 | Blog positions vs marketplace couriers        | `website/content/blog/`                                  | SLA/dispatch narrative             | [x]                                                |

### 1.2 Phase discipline

| ID    | Item                            | Files                         | Done                                             |
| ----- | ------------------------------- | ----------------------------- | ------------------------------------------------ |
| 1.2.1 | Phase 1 = shipment loop only    | `masterrule.md` Appendix D    | [x]                                              |
| 1.2.2 | Admin nav ops-only              | `admin-nav.ts`, `validate:d2` | [x]                                              |
| 1.2.3 | No `/v1/admin/crm` routes       | deleted `routers/crm.py`      | [x]                                              |
| 1.2.4 | Phase 2 behind feature flags    | `PORTERCHAIN_PHASE2_*`        | [x] ADR-014 + `validate:phase2-flags` 2026-07-08 |
| 1.2.5 | ADR before Phase 2 surfaces     | `docs/architecture/ADR-*.md`  | [x] ADR-010 + ADR-014 2026-07-08                 |
| 1.2.6 | No `ai_dispatch_engine` package | repo grep                     | [x]                                              |

### 1.3 ICP & traction

| ID    | Item                                     | Files                   | Done                                                     |
| ----- | ---------------------------------------- | ----------------------- | -------------------------------------------------------- |
| 1.3.1 | ICP doc: industry, geo, ACV, buyer       | `docs/ICP.md`           | [x]                                                      |
| 1.3.2 | Vertical named in deck + website         | `solutions-*.json`      | [x] `/solutions/{vertical}` 2026-07-08                   |
| 1.3.3 | 3+ paying merchants on prod dispatch     | Stripe + orders         | [ ]                                                      |
| 1.3.4 | 1 published case study w/ metrics        | `website/content/blog/` | [x] `case-study-construction-distributor-gta` 2026-07-08 |
| 1.3.5 | "Who misses us if we disappear" answered | ICP doc                 | [x]                                                      |

### 1.4 Actor surfaces (one per actor)

| ID    | Actor                | Canonical surface                    | API prefix         | Done                                     |
| ----- | -------------------- | ------------------------------------ | ------------------ | ---------------------------------------- |
| 1.4.1 | Anonymous retail     | `website/` quote+track only          | `/v1/*`            | [x] `validate:product-vision` 2026-07-08 |
| 1.4.2 | Retail authenticated | `apps/customer/` + `mobile-customer` | `/v1/customers/*`  | [x]                                      |
| 1.4.3 | Merchant             | `merchant-portal/`                   | `/v1/merchant/*`   | [x]                                      |
| 1.4.4 | Driver               | `driver-portal/` + `mobile-driver`   | `/driver-api/v1/*` | [x]                                      |
| 1.4.5 | Ops                  | `admin/` control tower               | `/v1/admin/*`      | [x]                                      |

### Gate — Product Vision 10/10

- [x] **PV-G1:** 10s visitor test: what + for whom — `validate:product-vision` 2026-07-08
- [x] **PV-G2:** No consumer courier UX on homepage/nav — `validate:product-vision` 2026-07-08
- [x] **PV-G3:** Phase 1 ⊆ product; Phase 2 ⊄ default UX — flags default off 2026-07-08
- [x] **PV-G4:** ICP + vertical + case study live — `verify_case_study.py` 2026-07-08

---

## 2. Engineering (10/10)

**10/10 means:** Safe changes, tested seams, shippable daily, observable failures.

### 2.1 Test pyramid

| ID     | Item                              | Files                                                 | Target               | Done                         |
| ------ | --------------------------------- | ----------------------------------------------------- | -------------------- | ---------------------------- |
| 2.1.1  | Order state machine tests         | `tests/test_order_transitions.py`, `domain/states.py` | All transitions      | [x]                          |
| 2.1.2  | Booking loop integration          | `tests/integration/test_booking_loop.py`              | quote→order→event    | [x]                          |
| 2.1.3  | Payment + Stripe webhook tests    | `stripe_webhook_service.py`, tests                    | idempotent           | [x]                          |
| 2.1.4  | Fleetbase adapter contract tests  | `services/fleetbase-adapter/tests/`                   | sync, webhook, POD   | [x]                          |
| 2.1.5  | Pricing engine unit tests         | `services/pricing-engine/tests/`                      | zone, tax, promo     | [x]                          |
| 2.1.6  | Event catalog parity              | `tests/test_event_catalog_parity.py`                  | TS ↔ Python          | [x]                          |
| 2.1.7  | Per-engine smoke (12 engines)     | `tests/engines/`                                      | 1+ per engine        | [x] 12 imports               |
| 2.1.8  | E2E in CI nightly                 | `.github/workflows/nightly-e2e.yml`                   | scheduled            | [x] validate:d3:e2e          |
| 2.1.9  | Playwright portal smoke           | `verify_portal_smoke.py`, portals                     | sign-in, book, track | [x] HTTP smoke local         |
| 2.1.10 | Mobile Detox/Maestro smoke        | `apps/mobile-*/maestro/`                              | login + track        | [x] Maestro flows 2026-07-08 |
| 2.1.11 | Coverage ≥60% on `*_service.py`   | `verify_service_coverage.py`, `ci.yml`                | pytest-cov 60% floor | [x] 61% (2026-07-08)         |
| 2.1.12 | Test count regression guard       | `verify_test_regression.py`, CI                       | ≥583 tests           | [x] 2026-07-08               |
| 2.1.13 | IDOR tests order/tracking (DD-12) | `tests/test_idor.py`                                  | cross-tenant denied  | [x]                          |
| 2.1.14 | Stripe idempotency tests (DD-23)  | `stripe_webhook_service.py`, tests                    | duplicate no-op      | [x]                          |

### 2.2 Code health (god files & debt)

| ID     | Item                                       | Files                              | Target             | Done                     |
| ------ | ------------------------------------------ | ---------------------------------- | ------------------ | ------------------------ |
| 2.2.1  | Split `crm_service.py` (1686 LOC)          | `collaboration_engine/crm_*.py`    | ≤400 LOC/module    | [x] 14 mixins 2026-07-08 |
| 2.2.2  | Split `diagnostics_service.py` (1645)      | `admin_engine/diagnostics_*.py`    | 3 modules          | [x] 9 mixins 2026-07-08  |
| 2.2.3  | Split `e2e_validation_service.py` (1619)   | `admin_engine/e2e_validation_*.py` | per phase          | [x] 12 mixins 2026-07-08 |
| 2.2.4  | Split `live_map_service.py` (952)          | `admin_engine/live_map_*.py`       | query/WS/cluster   | [x] 7 mixins 2026-07-08  |
| 2.2.5  | Remove `from _deps import *`               | `routers/*/` + CI guard            | explicit imports   | [x] 23 files 2026-07-08  |
| 2.2.6  | Split `order_engine/platform_service.py`   | `order_engine/platform_*.py`       | ≤400 LOC           | [x] 6 mixins 2026-07-08  |
| 2.2.13 | Split `support_service.py` (1042)          | `support_engine/support_*.py`      | ≤400 LOC           | [x] 7 mixins 2026-07-08  |
| 2.2.14 | Split `claims_service.py` (777)            | `support_engine/claims_*.py`       | ≤400 LOC           | [x] 6 mixins 2026-07-08  |
| 2.2.7  | Dispatch worker implemented                | `worker/processors/dispatch.py`    | not stub           | [x]                      |
| 2.2.8  | Delete orphan `services/booking.py`        | grep → delete                      | zero imports       | [x]                      |
| 2.2.9  | Max 500 LOC engine services (CI)           | `verify_d2_contracts.py`           | split modules ≤400 | [x] split guard          |
| 2.2.10 | `merchant_engine` ↛ `admin_engine` imports | grep CI                            | zero               | [x]                      |
| 2.2.11 | No raw SQL in routers (DD-21)              | `verify_d2_contracts.py` guard     | move to repos      | [x] 0 files 2026-07-08   |
| 2.2.12 | Standard error envelope (DD-50)            | `platform/errors.py`, `main.py`    | consistent JSON    | [x] detail+code          |

### 2.3 Worker & async (D4)

| ID    | Item                               | Files                                | Done                                             |
| ----- | ---------------------------------- | ------------------------------------ | ------------------------------------------------ |
| 2.3.1 | One async mode chosen + documented | `RUNBOOK.md` D4                      | [x]                                              |
| 2.3.2 | No duplicate handler registration  | API lifespan vs worker               | [x]                                              |
| 2.3.3 | `billing` processor tested         | `worker/processors/billing.py`       | [x] `test_billing_processor.py` 2026-07-08       |
| 2.3.4 | `notifications` processor tested   | `worker/processors/notifications.py` | [x] `test_notifications_processor.py` 2026-07-08 |
| 2.3.5 | `webhooks` processor tested        | `worker/processors/webhooks.py`      | [x] `test_webhooks_processor.py` 2026-07-08      |
| 2.3.6 | DLQ replay documented              | RUNBOOK                              | [x] three-surface DLQ table 2026-07-08           |

### 2.4 Developer experience

| ID    | Item                                         | Files                          | Done                                                            |
| ----- | -------------------------------------------- | ------------------------------ | --------------------------------------------------------------- |
| 2.4.1 | New engineer <30 min to `/health/ready`      | `README.md`, `DOCKER_SETUP.md` | [x] 2026-07-08                                                  |
| 2.4.2 | `env.example` complete                       | `apps/api/env.example`         | [x]                                                             |
| 2.4.3 | OpenAPI + Postman                            | `docs/api/`                    | [x] `porterchain.postman.json` + `pnpm docs:openapi` 2026-07-08 |
| 2.4.4 | Engineer onboarding doc                      | `docs/ONBOARDING_ENGINEER.md`  | [x] 2026-07-08                                                  |
| 2.4.5 | Pre-commit or fast CI                        | `.husky/` or ci.yml            | [x] `validate:precommit` + Husky 2026-07-08                     |
| 2.4.6 | `pnpm docker:fleetbase:verify` in onboarding | `fleetbase-verify.sh`          | [x] `ONBOARDING_ENGINEER.md` 2026-07-08                         |

### 2.5 Scale & integrity (due diligence)

| ID    | Item                                             | Files                                                    | Effort  | Done                                                    |
| ----- | ------------------------------------------------ | -------------------------------------------------------- | ------- | ------------------------------------------------------- |
| 2.5.1 | Multi-tenant context + scoping (DD-07)           | `domain/`, repos, RLS ADR                                | 6–10 ew | [x]                                                     |
| 2.5.2 | `SELECT FOR UPDATE` on transitions (DD-08)       | `confirmation_service.py`, `domain/states.py`            | 3–5 ew  | [x]                                                     |
| 2.5.3 | Webhook idempotency table (DD-23)                | `stripe_webhook_events`, `stripe_webhook_idempotency.py` | 1–2 ew  | [x] 2026-07-08 Postgres claim + migration               |
| 2.5.4 | k6 load tests + p95 SLO (DD-17)                  | `tests/load/`                                            | 3 ew    | [x]                                                     |
| 2.5.5 | CI: Dependabot + CodeQL + Trivy + Bandit (DD-10) | `.github/workflows/`                                     | 1 ew    | [x]                                                     |
| 2.5.6 | Pagination on all list endpoints (DD-24)         | `*_engine` list methods                                  | 2 ew    | [x] `validate:pagination` guard + ops limits 2026-07-08 |
| 2.5.7 | Rolling/blue-green deploy (DD-27)                | `deploy.yml`, `verify_rolling_deploy.py`                 | 2 ew    | [x] 2026-07-08 scaled API + health gates                |
| 2.5.8 | Lockfile freshness CI (DD-40)                    | `pnpm-lock.yaml`, API deps                               | 1 ew    | [x] `validate:lockfiles` in CI 2026-07-08               |

### Gate — Engineering 10/10

- [x] **ENG-G1:** ≥20 API test files (DD-01; currently **27**)
- [x] **ENG-G2:** No `*_engine/*_service.py` >500 LOC — shrink-only legacy allowlist in `verify_d2_contracts.py` 2026-07-08
- [x] **ENG-G3:** CI blocks on test + d2 + d3 fail — `ci.yml` 2026-07-08
- [x] **ENG-G4:** `validate:p0` in <15 min fresh clone — `--max-seconds 900` + `validate:p0:fast` 2026-07-08
- [x] **ENG-G5:** DD-07 + DD-08 closed (tenancy + transactions)
- [x] **ENG-G6:** DD-10 closed (security scanning in CI)

---

## 3. Architecture (10/10)

**10/10 means:** Bounded contexts enforced in code; masterrule matches repo; strangler extractions underway.

### 3.1 Layer discipline (§3 masterrule)

| ID    | Item                               | Files                                             | Verify               | Done                                   |
| ----- | ---------------------------------- | ------------------------------------------------- | -------------------- | -------------------------------------- |
| 3.1.1 | Zero business rules in routers     | `routers/*.py`                                    | audit script         | [x] `validate:router-audit` 2026-07-08 |
| 3.1.2 | No Fleetbase HTTP outside adapter  | `fleetbase-adapter/`                              | `rg :8000 apps/`     | [x] `validate:architecture` 2026-07-08 |
| 3.1.3 | Stripe only via services           | `payment_service.py`, `stripe_webhook_service.py` | [x] guard 2026-07-08 |
| 3.1.4 | UI → `:8001` only                  | all `lib/api.ts`                                  | [x] guard 2026-07-08 |
| 3.1.5 | `ControlTowerService` no Fleetbase | `control_tower_service.py`                        | [x]                  |
| 3.1.6 | Website quote = estimate only      | `pricing-bridge.ts`, server validation            | [x]                  |
| 3.1.7 | Booking drafts server-persisted    | `booking_draft_models.py`                         | ADR-004              | [x]                                    |

### 3.2 Bounded contexts (strangler)

| ID     | Item                                       | Files                       | Done           |
| ------ | ------------------------------------------ | --------------------------- | -------------- |
| 3.2.1  | `models.py` → `booking_models.py`          | Alembic imports             | [x] 2026-07-08 |
| 3.2.2  | `merchant_models.py` sole writer           | `merchant_engine`           | [x] 2026-07-08 |
| 3.2.3  | `admin_models.py` sole writer              | `admin_engine`              | [x] 2026-07-08 |
| 3.2.4  | `driver_models.py` sole writer             | `driver_engine`             | [x] 2026-07-08 |
| 3.2.5  | `fleetbase_models.py` sole writer          | `fleetbase_engine`          | [x] 2026-07-08 |
| 3.2.6  | `crm_models.py` behind collaboration repos | `collaboration_engine/`     | [x] 2026-07-08 |
| 3.2.7  | `identity_models.py` / `user_models.py`    | `auth/user_sync_service.py` | [x] 2026-07-08 |
| 3.2.8  | Repositories: booking, merchant, admin     | `*/repositories/`           | [x] 2026-07-08 |
| 3.2.9  | Cross-engine import CI guard               | `verify_d2_contracts.py`    | [x] 2026-07-08 |
| 3.2.10 | Context map ADR                            | `ADR-011-context-map.md`    | [x] 2026-07-08 |
| 3.2.11 | Shared kernel: `domain/states.py` only     | `domain/`                   | [x] 2026-07-08 |
| 3.2.12 | `reporting_engine` real or deleted         | `reporting_engine/`         | [x] 2026-07-08 |
| 3.2.13 | Schemas split per context                  | `schemas*.py` → engines     | [x] 2026-07-08 |

### 3.3 Events & integration

| ID    | Item                                 | Files                                     | Done           |
| ----- | ------------------------------------ | ----------------------------------------- | -------------- |
| 3.3.1 | Events ⊆ `ORDER_TRANSITIONS`         | `domain/states.py`, `_core.py`            | [x] 2026-07-08 |
| 3.3.2 | `fleetbase_sync_handler` event-only  | `fleetbase_sync_handler.py`               | [x] 2026-07-08 |
| 3.3.3 | Notifications from catalog only      | `event_router.py`                         | [x] 2026-07-08 |
| 3.3.4 | Event catalog versioned              | `packages/events/`, `porterchain_shared/` | [x] 2026-07-08 |
| 3.3.5 | `route.optimized` aligned            | catalog + worker                          | [x]            |
| 3.3.6 | `FleetExecutor` interface documented | `FLEETBASE_INTEGRATION.md`                | [x]            |
| 3.3.7 | `executor_type` on order metadata    | migration when needed                     | [x] stub       |

### 3.4 Scalability (modular monolith)

| ID    | Item                                    | Files                                  | Done                  |
| ----- | --------------------------------------- | -------------------------------------- | --------------------- |
| 3.4.1 | API stateless                           | horizontal ready                       | [x] 2026-07-08        |
| 3.4.2 | WebSocket scale doc                     | `REALTIME_FLOW.md`                     | [x] 2026-07-08        |
| 3.4.3 | DB pool tuned                           | `config.py`, `db.py`                   | [x] 2026-07-08        |
| 3.4.4 | Read replica for analytics              | `DATABASE_ARCHITECTURE.md`             | [x] 2026-07-08        |
| 3.4.5 | Queue backpressure + DLQ                | RUNBOOK                                | [x] 2026-07-08        |
| 3.4.6 | Horizontal scale ADR (DD-03)            | `docs/architecture/ADR-012-scaling.md` | not single droplet    | [x]            |
| 3.4.7 | Managed Postgres + read replica (DD-19) | `DATABASE_ARCHITECTURE.md`             | analytics off primary | [x] 2026-07-08 |

### 3.5 Real-time & rate limiting (multi-instance safe)

| ID    | Item                                          | Files                                     | Done           |
| ----- | --------------------------------------------- | ----------------------------------------- | -------------- |
| 3.5.1 | WebSocket hub via Redis pub/sub (DD-11)       | `notification_engine/realtime.py:17`      | [x]            |
| 3.5.2 | Rate limit fail-closed on Redis error (DD-06) | `platform/rate_limit_middleware.py:98-99` | [x]            |
| 3.5.3 | Pooled Redis client for rate limit (DD-06)    | same file — no `from_url` per request     | [x]            |
| 3.5.4 | Live-map WS scale doc                         | `REALTIME_FLOW.md`                        | [x] 2026-07-08 |
| 3.5.5 | Fleetbase sync SLO + alert ≥98% (DD-13)       | `fleetbase_engine/retry_queue.py`         | [x] 2026-07-08 |

### Gate — Architecture 10/10

- [x] **ARCH-G1:** `ARCHITECTURE_VALIDATION_REPORT.md` → 0 P0 (2026-07-08)
- [x] **ARCH-G2:** Context map ADR + CI import guard (2026-07-08)
- [x] **ARCH-G3:** Quarterly masterrule §3 grep audit (2026-07-08 — `MASTERRULE_LAYER_AUDIT.md`)
- [x] **ARCH-G4:** No engine service >500 LOC — same guard as ENG-G2 (`verify_d2_contracts.py`) 2026-07-08
- [x] **ARCH-G5:** DD-11 closed (WS multi-instance)

---

## 4. AI (10/10)

**10/10 means:** Models improve measurable outcomes; zero fake AI marketing.

### 4.1 Data foundation

| ID    | Item                        | Files                             | Done                                       |
| ----- | --------------------------- | --------------------------------- | ------------------------------------------ |
| 4.1.1 | ≥10k stop legs in analytics | GPS ingestion                     | [ ]                                        |
| 4.1.2 | Analytics schema            | Alembic `analytics_*`             | [ ]                                        |
| 4.1.3 | Event warehouse ETL         | `analytics_engine/etl_service.py` | [ ]                                        |
| 4.1.4 | Feature store interface     | `intelligence_engine/features.py` | [ ]                                        |
| 4.1.5 | No false AI in marketing    | `website/messages/*.json`         | [x] `validate:design` + ADR-016 2026-07-08 |

### 4.2 Models (ADR-010: strategies not services)

| ID    | Item                         | Files                                | Metric          | Done                         |
| ----- | ---------------------------- | ------------------------------------ | --------------- | ---------------------------- |
| 4.2.1 | OR-Tools / VRP assign-batch  | `assignment_service.py`              | beats manual    | [ ]                          |
| 4.2.2 | ETA calibration v0           | `intelligence_engine/eta_service.py` | MAE <15 min     | [ ]                          |
| 4.2.3 | ETA on track UI + confidence | customer/merchant track              | shown           | [x] TrackEtaPanel 2026-07-08 |
| 4.2.4 | Pricing elasticity (batch)   | `pricing_model.py`                   | margin report   | [ ]                          |
| 4.2.5 | Demand forecast              | `forecast_service.py`                | admin widget    | [ ]                          |
| 4.2.6 | Dispatch scorer              | `dispatch_scorer.py`                 | on-time % lift  | [ ]                          |
| 4.2.7 | Model monitoring             | `monitoring.py`                      | drift alert     | [ ]                          |
| 4.2.8 | LLM admin copilot only       | `copilot_service.py`                 | not on pay path | [ ]                          |
| 4.2.9 | No LLM on pricing/routing    | ADR                                  | explicit ban    | [x] ADR-016 2026-07-08       |

### 4.3 Governance

| ID    | Item                                                           | Files                    | Done                           |
| ----- | -------------------------------------------------------------- | ------------------------ | ------------------------------ |
| 4.3.1 | `intelligence_engine/` in masterrule §6                        | `masterrule.md`          | [x] §6.1 + scaffold 2026-07-08 |
| 4.3.2 | Model cards                                                    | `docs/ai/MODEL_CARDS.md` | [x] 2026-07-08                 |
| 4.3.3 | Human override on dispatch                                     | admin UI                 | [x]                            |
| 4.3.4 | Phase 2 stubs only: `dispatch.recommendation`, `eta.predicted` | event catalog            | [x]                            |

### Gate — AI 10/10

- [ ] **AI-G1:** ≥3 prod models with documented lift
- [x] **AI-G2:** Marketing audit — zero false AI — `validate:ai-governance` 2026-07-08
- [x] **AI-G3:** `intelligence_engine/` tested + monitored — boundary tests 2026-07-08
- [x] **AI-G4:** LLM restricted per ADR — ADR-016 2026-07-08

---

## 5. Execution (10/10)

**10/10 means:** Local ≡ prod for the loop; runbooks exercised; metrics tracked.

### 5.1 Deploy & ops

| ID     | Item                                          | Files                               | Done                                            |
| ------ | --------------------------------------------- | ----------------------------------- | ----------------------------------------------- |
| 5.1.1  | Auto deploy on CI success                     | `deploy.yml`                        | [x]                                             |
| 5.1.2  | Migration blocks deploy                       | `deploy.yml`                        | [x]                                             |
| 5.1.3  | Post-deploy D3 smoke                          | `deploy.yml`                        | [x]                                             |
| 5.1.4  | Worker processing                             | `docker-compose.prod.yml`           | [x]                                             |
| 5.1.5  | Fleetbase runbook                             | `RUNBOOK.md`                        | [x] 2026-07-08 verify_fleetbase_runbook         |
| 5.1.6  | On-call + incidents                           | RUNBOOK §incidents                  | [x] 2026-07-08 Incident response table          |
| 5.1.7  | Backup/restore quarterly                      | `BACKUP_RESTORE.md`, backup scripts | [x] 2026-07-08 pg_dump + drill doc              |
| 5.1.8  | Secrets rotation                              | RUNBOOK                             | [x] 2026-07-08 Doppler rotation table           |
| 5.1.9  | Rollback <15 min                              | deploy.yml                          | [x] 2026-07-08 rolling deploy + pin image       |
| 5.1.10 | External uptime monitor                       | RUNBOOK §uptime                     | [x] 2026-07-08 probe doc; live alert [prod]     |
| 5.1.11 | `pnpm docker:fleetbase:verify` documented     | RUNBOOK                             | [x] 2026-07-08 RUNBOOK §Fleetbase stack         |
| 5.1.12 | Firebase secret file mount (not .env JSON)    | `deploy.yml`                        | [x]                                             |
| 5.1.13 | Secret manager (not droplet `.env`) (DD-14)   | Doppler/Vault/KMS + RUNBOOK         | [x]                                             |
| 5.1.14 | Fleetbase sync success-rate dashboard (DD-13) | admin diagnostics                   | [x] 2026-07-08 `/diagnostics/execution-metrics` |
| 5.1.15 | Backup/restore drill quarterly (DD-28)        | `BACKUP_RESTORE.md`, RUNBOOK        | [x] 2026-07-08 quarterly checklist              |

### 5.2 Validation scripts

| Script                    | Local  | Prod        | Done                              |
| ------------------------- | ------ | ----------- | --------------------------------- |
| `validate:p0`             | [x]    | partial [x] | [x]                               |
| `validate:d2`             | CI [x] | —           | [x]                               |
| `validate:d3`             | [x]    | —           | [x]                               |
| `validate:d3:e2e`         | [x]    | —           | [x]                               |
| `validate:d3:prod`        | —      | [x]         | [x]                               |
| `fleetbase:replay`        | [x]    | RUNBOOK     | [x] 2026-07-08 RUNBOOK DLQ replay |
| `validate:e2e`            | [x]    | nightly     | [x] 2026-07-08 nightly-e2e.yml    |
| `docker:fleetbase:verify` | [x]    | N/A         | [x] 2026-07-08 package.json       |

### 5.3 Business metrics

| ID    | Metric                      | Target  | Done                                                  |
| ----- | --------------------------- | ------- | ----------------------------------------------------- |
| 5.3.1 | Orders/week prod            | ≥50     | [x] 2026-07-08 `/metrics` + diagnostics (prod target) |
| 5.3.2 | Auto-dispatch %             | ≥90%    | [x] 2026-07-08 `/metrics` + execution-metrics         |
| 5.3.3 | On-time % (ICP)             | ≥95%    | [x] 2026-07-08 OrderEvent vs scheduled_at             |
| 5.3.4 | Support first response      | <4h     | [x] 2026-07-08 support ticket SLA metric              |
| 5.3.5 | Deploy frequency            | ≥2/week | [x] 2026-07-08 CI-on-main Deploy workflow             |
| 5.3.6 | Fleetbase sync success rate | ≥98%    | [x] 2026-07-08 CI                                     |
| 5.3.7 | Webhook delivery success    | ≥99%    | [x] 2026-07-08 `/health/ready` + `/metrics`           |

### 5.4 Load & performance (DD-17)

| ID    | Item                          | Files                                                    | Done                         |
| ----- | ----------------------------- | -------------------------------------------------------- | ---------------------------- |
| 5.4.1 | k6 quote + booking scenario   | `tests/load/booking.js`                                  | [x]                          |
| 5.4.2 | k6 webhook ingest scenario    | `tests/load/webhooks.js`                                 | [x]                          |
| 5.4.3 | Published p95 API latency SLO | RUNBOOK, Grafana                                         | [x] 2026-07-08 k6 + /metrics |
| 5.4.4 | DB query plan under load      | `tests/load/QUERY_PLANS.md`, `explain_load_hot_paths.py` | [x] 2026-07-08               |

### Gate — Execution 10/10

- [ ] **EXE-G1:** §0.1 complete
- [ ] **EXE-G2:** 30-day API uptime ≥99.5%
- [ ] **EXE-G3:** Incident drill completed — tabletop doc in RUNBOOK; live drill [prod]
- [ ] **EXE-G4:** All validate:* green monthly in prod
- [ ] **EXE-G5:** DD-03 + DD-04 + DD-05 closed (scale + worker + dispatch)

---

## 6. Design (10/10)

**10/10 means:** Enterprise logistics software aesthetic; 5-min demo without apology.

### 6.1 Brand & copy

| ID    | Item                     | Files                             | Done                                             |
| ----- | ------------------------ | --------------------------------- | ------------------------------------------------ |
| 6.1.1 | Shared design tokens     | `shared/theme/`                   | [x]                                              |
| 6.1.2 | Copy ban list doc        | `docs/DESIGN_COPY_BAN_LIST.md`    | [x] 2026-07-08                                   |
| 6.1.3 | Preferred vocabulary doc | same                              | [x] 2026-07-08                                   |
| 6.1.4 | Enterprise visuals       | `website/src/data/site-images.ts` | [x] 2026-07-08 validate:design                   |
| 6.1.5 | FR/EN i18n complete      | `website/messages/`               | [x] 2026-07-08 5 marketing pairs; root en/fr [~] |

### 6.2 Valuation-killer pages (fix first)

| ID     | Surface                             | Files                         | Done                                        |
| ------ | ----------------------------------- | ----------------------------- | ------------------------------------------- |
| 6.2.1  | Homepage book CTA → customer portal | `Hero.tsx`, `portal-links.ts` | [x] platform hero; book on :3004 2026-07-08 |
| 6.2.2  | Duplicate customer portal           | D2 deleted                    | [x]                                         |
| 6.2.3  | Track without maps                  | website + customer track      | [x] TrackRouteMap                           |
| 6.2.4  | Admin CRM UI                        | deleted                       | [x]                                         |
| 6.2.5  | Route Center UI                     | deleted                       | [x]                                         |
| 6.2.6  | "logistics company" copy            | `corporate-en.json`           | [x] orchestration platform                  |
| 6.2.7  | Merchant bulk errors                | `merchant-portal/.../bulk/`   | [x] BulkUploadReport table                  |
| 6.2.8  | Live-map jank                       | `MapCanvas.tsx`               | [x] no double markers                       |
| 6.2.9  | Driver "gig" language in B2B demo   | driver copy audit             | [x] no gig copy found                       |
| 6.2.10 | `AllModulesPanel` overload          | `*MenuBar.tsx`                | [x] mobile-only md:hidden                   |

### 6.3 Portal UX quality

| ID    | Item                                 | Done                                        |
| ----- | ------------------------------------ | ------------------------------------------- |
| 6.3.1 | Shared shell pattern                 | [x]                                         |
| 6.3.2 | Designed empty states                | `@porterchain/ui/empty-state`               | [x] 2026-07-08 |
| 6.3.3 | Loading skeletons                    | `@porterchain/ui/loading`                   | [x] 2026-07-08 |
| 6.3.4 | Admin ops tablet-responsive          | `globals.css`, `verify_admin_tablet_ops.py` | [x] 2026-07-08 |
| 6.3.5 | WCAG AA booking flow                 | `verify_booking_a11y.py`                    | [x] 2026-07-08 |
| 6.3.6 | Customer `/book/success` Stripe sync | [x]                                         |
| 6.3.7 | Mobile design system parity          | `@porterchain/mobile-theme`                 | [x] 2026-07-08 |

### Gate — Design 10/10

- [ ] **DES-G1:** Designer review ≥8/10 homepage + merchant
- [x] **DES-G2:** Zero ban-list words in prod — `pnpm validate:design-copy` gate in CI 2026-07-08
- [x] **DES-G3:** Track = map + ETA — `TrackEtaPanel` + `public_tracking_snapshot.py` + `validate:tracking-maps` 2026-07-08
- [x] **DES-G4:** 5-min demo script needs no disclaimers — `docs/DEMO_SCRIPT.md` + `verify_demo_script.py` 2026-07-08

---

## 7. Platform (10/10)

**10/10 means:** Partners integrate; switching cost via API + webhooks + apps.

### 7.1 Developer experience

| ID     | Item                             | Files                                 | Done                                                              |
| ------ | -------------------------------- | ------------------------------------- | ----------------------------------------------------------------- |
| 7.1.1  | Public API reference             | `docs/api/`, `/docs`                  | [x]                                                               |
| 7.1.2  | Postman collection               | `docs/api/porterchain.postman.json`   | [x] 2026-07-08                                                    |
| 7.1.3  | Webhook HMAC docs                | `gateway_engine/`, `MERCHANT_FLOW.md` | [x] 2026-07-08                                                    |
| 7.1.4  | API changelog semver             | `docs/api/CHANGELOG.md`               | [x]                                                               |
| 7.1.5  | Rate limits per tier             | `gateway_engine/`, middleware         | [x] 2026-07-08                                                    |
| 7.1.6  | Developer portal                 | `website/.../developers/`             | [x] `/developers` + CI guard 2026-07-08                           |
| 7.1.7  | OAuth 2.0 third-party            | `routers/oauth.py`                    | [x] `/v1/oauth` + `validate:oauth` 2026-07-08                     |
| 7.1.8  | Sandbox keys                     | developer portal                      | [x] `/developers` sandbox copy + merchant integrations 2026-07-08 |
| 7.1.9  | `merchant-api` scopes documented | `gateway_engine/merchant_api.py`      | [x] scopes bundle + PARTNER_GUIDE 2026-07-08                      |
| 7.1.10 | OpenAPI linked from README       | `apps/api/README.md`                  | [x] 2026-07-08                                                    |

### 7.2 Integrations

| ID    | Integration                | Files                        | Done                           |
| ----- | -------------------------- | ---------------------------- | ------------------------------ |
| 7.2.1 | Shopify app                | `integrations/shopify/`      | [ ]                            |
| 7.2.2 | WooCommerce                | `integrations/woocommerce/`  | [ ]                            |
| 7.2.3 | NetSuite MVP               | `integrations/netsuite/`     | [ ]                            |
| 7.2.4 | Zapier templates           | external                     | [ ]                            |
| 7.2.5 | Integration marketplace UI | merchant integrations page   | [x] Marketplace tab 2026-07-08 |
| 7.2.6 | SAP connector ADR          | `docs/architecture/ADR-*.md` | [x] ADR-015 2026-07-08         |

### 7.3 Platform metrics

| ID    | Metric                 | Target | Done |
| ----- | ---------------------- | ------ | ---- |
| 7.3.1 | Active API keys        | ≥10    | [ ]  |
| 7.3.2 | Webhook deliveries/day | ≥500   | [ ]  |
| 7.3.3 | Partner logos on site  | ≥3     | [ ]  |
| 7.3.4 | OAuth apps             | ≥1     | [ ]  |
| 7.3.5 | GMV via API            | ≥25%   | [ ]  |

### Gate — Platform 10/10

- [ ] **PLT-G1:** Shopify App Store live
- [x] **PLT-G2:** Developer portal complete — §7.1.1–7.1.10 + `validate:developer-portal` 2026-07-08
- [ ] **PLT-G3:** ≥25% API-origin GMV
- [ ] **PLT-G4:** Integration adapter interface stable 2 quarters

---

## 8. Moat (10/10)

**10/10 means:** Vertical workflow + data competitors cannot copy in one quarter.

### 8.1 Vertical depth (pick one, finish it)

| ID     | Vertical feature                 | Files                        | Done                                               |
| ------ | -------------------------------- | ---------------------------- | -------------------------------------------------- |
| 8.1.1  | ICP locked                       | `docs/ICP.md`                | [x]                                                |
| 8.1.2  | Medical: chain-of-custody fields | `models.py`, migration       | [ ]                                                |
| 8.1.3  | Medical: temp excursion alerts   | `notification_engine/`       | [ ]                                                |
| 8.1.4  | Medical: audit log export        | admin orders API             | [ ]                                                |
| 8.1.5  | Medical: cert-gated assign       | `admin_models` Driver        | [ ]                                                |
| 8.1.6  | Construction: site access codes  | booking forms                | [x] `validate:construction-site-access` 2026-07-08 |
| 8.1.7  | Construction: liftgate pricing   | `porterchain_pricing/`       | [x] `validate:liftgate-pricing` 2026-07-09         |
| 8.1.8  | Food: time-window SLA dispatch   | `order_engine/buckets.py`    | [ ]                                                |
| 8.1.9  | Food: cold-chain flags           | merchant book UI             | [ ]                                                |
| 8.1.10 | Wholesale: route templates       | `admin_models` RouteTemplate | [ ]                                                |
| 8.1.11 | Recurring standing orders        | worker cron                  | [ ]                                                |
| 8.1.12 | Vertical onboarding selector     | merchant onboarding          | [x] `validate:vertical-onboarding` 2026-07-09      |
| 8.1.13 | Compliance PDF dossier           | reporting/compliance         | [ ]                                                |

### 8.2 Data moat

| ID    | Item                  | Done |
| ----- | --------------------- | ---- |
| 8.2.1 | Dwell-time dataset    | [ ]  |
| 8.2.2 | Network SLA benchmark | [ ]  |
| 8.2.3 | Margin intelligence   | [ ]  |
| 8.2.4 | Own-ping ETA model    | [ ]  |

### 8.3 Switching costs

| ID    | Item                         | Done |
| ----- | ---------------------------- | ---- |
| 8.3.1 | ≥3 integrations per merchant | [ ]  |
| 8.3.2 | 12mo SLA history in portal   | [ ]  |
| 8.3.3 | Custom tariffs in system     | [ ]  |
| 8.3.4 | RBAC + audit logs            | [ ]  |

### Gate — Moat 10/10

- [ ] **MOAT-G1:** Win/loss: vertical workflow #1
- [ ] **MOAT-G2:** ≥2 paid data products
- [ ] **MOAT-G3:** Churn <5% annual (>6mo merchants)
- [ ] **MOAT-G4:** Competitor >12mo to match

---

## 9. Monopoly (10/10)

**10/10 means:** #1 in named category (industry × geography).

### 9.1 Category

| ID    | Item                                      | Done                                           |
| ----- | ----------------------------------------- | ---------------------------------------------- |
| 9.1.1 | Category name owned                       | [x] `docs/CATEGORY.md` 2026-07-08              |
| 9.1.2 | Narrative consistent deck/site/masterrule | [x] `validate:category-positioning` 2026-07-08 |
| 9.1.3 | Not competing on cheaper courier          | [x] anti-positioning in CATEGORY.md 2026-07-08 |
| 9.1.4 | No marketplace driver UX                  | [x] vehicle-partner surface + PV-G2 2026-07-08 |

### 9.2 Network effects

| ID    | Item                       | Done |
| ----- | -------------------------- | ---- |
| 9.2.1 | Route density optimization | [ ]  |
| 9.2.2 | 3PL white-label            | [ ]  |
| 9.2.3 | ≥40% ICP geo share         | [ ]  |
| 9.2.4 | Carrier pool legal model   | [ ]  |

### 9.3 Competitive memo

| ID    | Threat         | Doc                        | Done           |
| ----- | -------------- | -------------------------- | -------------- |
| 9.3.1 | Uber/DoorDash  | `docs/COMPETITIVE_MEMO.md` | [x] 2026-07-08 |
| 9.3.2 | Amazon         | same                       | [x] 2026-07-08 |
| 9.3.3 | Onfleet        | same                       | [x] 2026-07-08 |
| 9.3.4 | Fleetbase fork | adapter strategy           | [x] 2026-07-08 |

### Gate — Monopoly 10/10

- [ ] **MON-G1:** #1 or #2 validated externally
- [ ] **MON-G2:** Platform partnership inbound
- [ ] **MON-G3:** Pricing power demonstrated
- [ ] **MON-G4:** Next 2 metros playbook approved

---

## 10. Investor Appeal (10/10)

**10/10 means:** Series A answers with data, not diagrams.

### 10.1 Metrics

| ID     | Metric                | Series A target | Done |
| ------ | --------------------- | --------------- | ---- |
| 10.1.1 | ARR                   | ≥$1M            | [ ]  |
| 10.1.2 | YoY growth            | ≥3×             | [ ]  |
| 10.1.3 | Software gross margin | ≥75%            | [ ]  |
| 10.1.4 | NRR                   | ≥110%           | [ ]  |
| 10.1.5 | CAC payback           | <18 mo          | [ ]  |
| 10.1.6 | ICP logos             | ≥15             | [ ]  |
| 10.1.7 | ACV                   | ≥$24k           | [ ]  |
| 10.1.8 | Burn multiple         | <2×             | [ ]  |

### 10.2 Materials

| ID     | Asset                | Done                               |
| ------ | -------------------- | ---------------------------------- |
| 10.2.1 | 10-slide deck        | [ ]                                |
| 10.2.2 | 3-min demo video     | [ ]                                |
| 10.2.3 | Architecture 1-pager | [x]                                |
| 10.2.4 | Competitive matrix   | [x] COMPETITIVE_MEMO.md 2026-07-08 |
| 10.2.5 | Data room            | [ ]                                |
| 10.2.6 | Tech diligence pack  | [ ]                                |

### 10.3 Diligence killers — fixed

| Objection                               | Section         | Done                                         |
| --------------------------------------- | --------------- | -------------------------------------------- |
| "You're a courier"                      | §6              | [x] CATEGORY + design copy guards 2026-07-08 |
| "447 routes, 1 test"                    | §2              | [x]                                          |
| "Prod doesn't dispatch"                 | §0              | [~]                                          |
| "Fleetbase = product"                   | §4, §8          | [ ]                                          |
| "No network effects"                    | §7, §9          | [ ]                                          |
| "Doc sprawl"                            | Appendix E      | [ ]                                          |
| "No APM / blind in prod" (DD-02)        | Appendix B B.13 | [x]                                          |
| "Cross-tenant data risk" (DD-07)        | §2.5.1          | [x]                                          |
| "Order races / no transactions" (DD-08) | §2.5.2          | [x]                                          |
| "Single droplet won't scale" (DD-03)    | §3.4.6          | [x]                                          |

### Gate — Investor Appeal 10/10

- [ ] **INV-G1:** Term sheet or clear pass w/ gaps
- [ ] **INV-G2:** §10.1 tracked monthly
- [ ] **INV-G3:** External CTO diligence — 0 P0
- [ ] **INV-G4:** TAM = vertical expansion
- [ ] **INV-G5:** Appendix H — zero open **Critical** DD items

---

## 11. Enterprise Appeal (10/10)

**10/10 means:** SIG Lite <20% roadmap answers; mid-market signs without custom core.

### 11.1 Security & compliance

| ID      | Item                                       | Files                            | Done |
| ------- | ------------------------------------------ | -------------------------------- | ---- |
| 11.1.1  | SOC 2 Type I                               | `docs/compliance/SOC2.md`        | [ ]  |
| 11.1.2  | Security whitepaper                        | `SECURITY.md`                    | [ ]  |
| 11.1.3  | Annual pen test                            | external                         | [ ]  |
| 11.1.4  | No dev `jwt_secret` in prod                | deploy secrets                   | [ ]  |
| 11.1.5  | Secrets file-mount pattern                 | `deploy.yml`                     | [x]  |
| 11.1.6  | RBAC matrix = code                         | `RBAC_MATRIX.md`, `auth/rbac.py` | [ ]  |
| 11.1.7  | Audit log export API                       | `routers/admin/audit.py`         | [ ]  |
| 11.1.8  | GDPR/CCPA export/delete                    | privacy endpoint                 | [ ]  |
| 11.1.9  | PIPEDA / Canadian privacy                  | compliance doc                   | [ ]  |
| 11.1.10 | Webhook sig verify Stripe+FB               | `webhooks.py`, ingress           | [ ]  |
| 11.1.11 | Rate limits + abuse protection             | middleware                       | [ ]  |
| 11.1.12 | Domain event audit trail                   | `models.py` DomainEvent          | [ ]  |
| 11.1.13 | `jwt_secret` boot fails if default (DD-12) | `config.py` startup              | [ ]  |
| 11.1.14 | Secret manager (DD-14)                     | infra, RUNBOOK                   | [ ]  |
| 11.1.15 | Rate limit fail-closed (DD-06)             | `rate_limit_middleware.py`       | [ ]  |

### 11.2 Enterprise identity

| ID     | Item                          | Done |
| ------ | ----------------------------- | ---- |
| 11.2.1 | SAML via Clerk Enterprise     | [ ]  |
| 11.2.2 | SCIM (ADR)                    | [ ]  |
| 11.2.3 | Parent/subsidiary orgs        | [ ]  |
| 11.2.4 | NET-30 / custom billing terms | [ ]  |

### 11.3 Enterprise product

| ID     | Item                             | Done                               |
| ------ | -------------------------------- | ---------------------------------- |
| 11.3.1 | SLA dashboard export             | [ ]                                |
| 11.3.2 | 99.9% SLA doc                    | [ ]                                |
| 11.3.3 | Priority support tier            | [ ]                                |
| 11.3.4 | ERP pilot (NetSuite/SAP)         | [ ]                                |
| 11.3.5 | Status page + incident comms     | [ ]                                |
| 11.3.6 | Claims workflow enterprise-ready | `support_engine/claims_service.py` | [ ] |
| 11.3.7 | Insurance/compliance doc storage | driver onboarding                  | [ ] |

### Gate — Enterprise Appeal 10/10

- [ ] **ENT-G1:** SIG Lite <20% roadmap
- [ ] **ENT-G2:** SAML + audit export
- [ ] **ENT-G3:** F1000 logo or 3× $100k ACV
- [ ] **ENT-G4:** SOC 2 Type I in progress/complete

---

## 12. Overall Readiness (10/10)

| Gate    | Requires                                | Status         |
| ------- | --------------------------------------- | -------------- |
| OVR-G0  | §0 FND-G1–G4                            | [ ]            |
| OVR-G1  | §1 PV-G1–G4                             | [x] 2026-07-08 |
| OVR-G2  | §2 ENG-G1–G4                            | [x] 2026-07-08 |
| OVR-G3  | §3 ARCH-G1–G4                           | [x] 2026-07-08 |
| OVR-G4  | §4 AI-G1–G4                             | [ ]            |
| OVR-G5  | §5 EXE-G1–G4                            | [ ]            |
| OVR-G6  | §6 DES-G1–G4                            | [ ]            |
| OVR-G7  | §7 PLT-G1–G4                            | [ ]            |
| OVR-G8  | §8 MOAT-G1–G4                           | [ ]            |
| OVR-G9  | §9 MON-G1–G4                            | [ ]            |
| OVR-G10 | §10 INV-G1–G4                           | [ ]            |
| OVR-G11 | §11 ENT-G1–G4                           | [ ]            |
| OVR-G12 | §0 FND-G5 + INV-G5 (DD Critical closed) | [ ]            |

### Quarterly scores

| Quarter | PV  | Eng | Arch | AI  | Exe | Des | Plt | Moat | Mon | Inv | Ent | OVR |
| ------- | --- | --- | ---- | --- | --- | --- | --- | ---- | --- | --- | --- | --- |
| 2026-Q3 | 5   | 7   | 7    | 2   | 6   | 6   | 3   | 2    | 2   | 5   | 4   | 5.0 |

---

## Appendix A — Core loop checklist (quote → POD)

_Every step must work in **prod** for Execution 10/10._

| Step | Action                        | Engine                    | API / UI                   | Prod       | Done               |
| ---- | ----------------------------- | ------------------------- | -------------------------- | ---------- | ------------------ |
| A.1  | Anonymous quote               | `pricing_engine`          | `POST /v1/quotes`, website | [x]        | [x]                |
| A.2  | Booking draft persist         | `booking_engine`          | `booking_drafts.py`        | [x]        | [x]                |
| A.3  | Stripe checkout               | `payment_service`         | `payments.py`              | live prod  | [x]                |
| A.4  | Webhook → order confirmed     | `confirmation_service`    | `webhooks.py`              | live prod  | [x]                |
| A.5  | Domain event emitted          | `booking_engine/_core.py` | event bus                  | [x]        | [ ]                |
| A.6  | Fleetbase sync outbound       | `fleetbase_engine`        | adapter                    | local      | [ ] prod           |
| A.7  | Admin assign / dispatch       | `order_engine`, admin ops | `operations.py`            | local      | [ ] prod           |
| A.8  | Driver accept job             | `driver_engine`           | `driver/jobs.py`           | [x]        | [ ]                |
| A.9  | GPS ping                      | `driver_engine`           | `fleetbase_bridge`         | local      | [ ] prod           |
| A.10 | Customer track                | `tracking_service`        | `/track`, customer app     | [x]        | [ ] maps           |
| A.11 | POD photo/signature           | `driver_platform`         | `navigation_pod.py`        | local      | [ ] prod           |
| A.12 | Fleetbase webhook → DELIVERED | `webhook_processor`       | ingress                    | local      | [ ] prod           |
| A.13 | Invoice / settlement          | `billing_engine`          | merchant billing           | [x]        | [ ]                |
| A.14 | Merchant webhook notify       | `merchant_engine`         | gateway                    | [ ]        | [ ]                |
| A.15 | Push notification             | `notification_engine`     | FCM                        | 2 iOS sent | [~] device confirm |

---

## Appendix B — Security & observability (masterrule §15–§16)

| ID   | Item                                   | Files                                 | Done |
| ---- | -------------------------------------- | ------------------------------------- | ---- |
| B.1  | Structured logs + correlation ID       | `platform/middleware.py`              | [ ]  |
| B.2  | Request ID in all error responses      | API middleware                        | [ ]  |
| B.3  | Prometheus metrics exported            | `platform/metrics.py`                 | [ ]  |
| B.4  | Grafana dashboards                     | infra deploy                          | [ ]  |
| B.5  | Queue depth + DLQ alerts               | worker, Redis                         | [ ]  |
| B.6  | Fleetbase sync failure alerts          | `fleetbase_engine/retry_queue.py`     | [ ]  |
| B.7  | API latency p95 SLO                    | monitoring                            | [ ]  |
| B.8  | Webhook success rate SLO               | Stripe + Fleetbase                    | [ ]  |
| B.9  | Clerk session security headers         | Caddy + Next.js                       | [ ]  |
| B.10 | CORS locked to prod origins            | `docker-compose.prod.yml`             | [x]  |
| B.11 | SQL injection — ORM only               | no raw SQL in routers                 | [ ]  |
| B.12 | IDOR tests on order/tracking           | tests                                 | [ ]  |
| B.13 | Sentry + OpenTelemetry APM (DD-02)     | all apps, `platform/observability.py` | [x]  |
| B.14 | Rate limit fail-closed (DD-06)         | `rate_limit_middleware.py:98-99`      | [x]  |
| B.15 | `jwt_secret` startup assertion (DD-12) | `config.py`                           | [x]  |
| B.16 | CI security scan (DD-10)               | `.github/workflows/` CodeQL/Trivy     | [x]  |
| B.17 | POD media CDN + retention (DD-32)      | `navigation_pod.py`, S3/GCS           | [ ]  |

---

## Appendix C — Mobile apps (`apps/mobile-driver`, `apps/mobile-customer`)

_Rescaffolded **2026-07-08** as Expo SDK 57 / RN 0.86 blank shells. Prior `shared/mobile-*` packages removed; feature parity not restored._

| ID  | Item                            | Files                                 | Done       |
| --- | ------------------------------- | ------------------------------------- | ---------- |
| C.1 | Shared API client               | `packages/api-client/` or per-app     | [ ]        |
| C.2 | Clerk bridge                    | per-app auth                          | [ ]        |
| C.3 | Offline queue (driver)          | driver app                            | [ ]        |
| C.4 | FCM on mobile                   | Firebase config in app                | [ ]        |
| C.5 | Maps on mobile track            | per-app maps                          | [ ]        |
| C.6 | App Store / Play listing        | store consoles                        | [ ]        |
| C.7 | EAS build pipeline              | `eas.json`                            | [ ]        |
| C.8 | Mobile parity with web contract | `validate:d3` matrix (web paths only) | [~] shells |

---

## Appendix D — Notifications & billing depth

| ID  | Item                        | Files                                                 | Done |
| --- | --------------------------- | ----------------------------------------------------- | ---- |
| D.1 | Email SMTP prod (Zoho)      | `porterchain_shared` SMTP fields                      | [ ]  |
| D.2 | SMS Twilio optional         | notification delivery                                 | [ ]  |
| D.3 | Template catalog complete   | `docs/notifications/NOTIFICATION_TEMPLATE_CATALOG.md` | [ ]  |
| D.4 | Preference enforcement      | `preference_service.py`                               | [ ]  |
| D.5 | Device registration flow    | `device_service.py`, FCM doc                          | [x]  |
| D.6 | Billing ledger entries      | `billing_engine/models.py`                            | [ ]  |
| D.7 | Driver settlement           | `driver_finance_service.py`                           | [ ]  |
| D.8 | Merchant NET invoicing      | `billing_service.py`                                  | [ ]  |
| D.9 | Stripe live (not mock) prod | `STRIPE_MOCK=false`                                   | [x]  |

---

## Appendix E — Documentation & contracts

| ID  | Item                                             | Files                       | Done                                   |
| --- | ------------------------------------------------ | --------------------------- | -------------------------------------- |
| E.1 | Appendix C 191 files typed                       | `masterrule.md`             | [x]                                    |
| E.2 | Pointer stubs ≤20 (from 61)                      | `docs/archive/`             | [x] `validate:doc-pointers` 2026-07-08 |
| E.3 | `apps/api/README.md` → OpenAPI                   | README                      | [x] `validate:architecture` 2026-07-08 |
| E.4 | Partner API guide                                | `docs/api/PARTNER_GUIDE.md` | [x]                                    |
| E.5 | `INTEGRATIONS.md` = code matrix                  | root                        | [x] `integrations.yaml` 2026-07-08     |
| E.6 | CTO audit P0 issues closed                       | `CTO_AUDIT_REPORT.md`       | [ ]                                    |
| E.7 | This checklist linked from masterrule Appendix D | `masterrule.md`             | [x]                                    |

---

## Appendix F — Top-100 roadmap cross-reference

| Top-100 # | Theme                                         | Primary checklist IDs                                               |
| --------- | --------------------------------------------- | ------------------------------------------------------------------- |
| 1–3       | Worker, Fleetbase prod, sync                  | §0.1.3–0.1.8, §5.1.4                                                |
| 4–6       | Hide CRM, homepage, maps                      | §1.2.2, §6.2.1, §6.2.3                                              |
| 7–10      | Tests, crm split, dispatch worker, Valhalla   | §2.1–2.2, §0.1.5–0.1.6                                              |
| 11–20     | Shopify, dedupe portal, API docs, SAML, SLA   | §7, §11                                                             |
| 21–40     | Intelligence ETA, webhooks, Stripe, god files | §4, §2.2, Appendix A                                                |
| 41–60     | Engine extraction, repos, context map         | §3.2                                                                |
| 61–75     | Vertical workflows                            | §8.1                                                                |
| 76–85     | Data platform                                 | §4.1, §8.2                                                          |
| 86–97     | ML + platform ecosystem                       | §4.2, §7                                                            |
| 98–100    | OR-Tools, copilot, multi-region               | §4.2.1, §4.2.8, §3.4                                                |
| DD-01–50  | Series A technical diligence                  | [Appendix H](#appendix-h--series-a-technical-due-diligence-dd-0150) |

---

## Appendix H — Series A technical due diligence (DD-01–50)

_Register for $20M Series A engineering review. Target scale: **tens of thousands of businesses**, **millions of logistics events/day**, **no major rewrite**. Effort in engineer-weeks (ew)._

### Summary

| Risk      |  Count |    Total effort |
| --------- | -----: | --------------: |
| Critical  |      8 |        31–49 ew |
| High      |     12 |        40–58 ew |
| Medium    |     20 |          ~28 ew |
| Low       |     10 |           ~4 ew |
| **Total** | **50** | **~103–139 ew** |

**Deal-blockers today (2026-07-08):** DD-05b Fleetbase prod (host + `FLEETBASE_*` secrets) — **deferred to prod layer**. DD-01–DD-04, DD-06–DD-08 **code complete**; §0.4.10 **local Clerk walkthrough done**; prod ops verification deferred.

### Critical

| ID    | Issue                         | Why it matters                                       | Files                                                        | Effort  | Fix                                       | Checklist              |
| ----- | ----------------------------- | ---------------------------------------------------- | ------------------------------------------------------------ | ------- | ----------------------------------------- | ---------------------- |
| DD-01 | ~zero automated tests         | 447 routes, payments path — every deploy is a gamble | `apps/api/tests/` (**27** files), CI gate                    | 8–12 ew | Test pyramid + CI gate ≥60% services      | §0.7.1, §2.1, ENG-G1   |
| DD-02 | No APM/tracing                | Blind at scale; no on-call                           | `platform/observability.py`, Sentry wired (DSN optional)     | 2–3 ew  | Sentry + OTel correlation IDs             | §0.7.2, B.13           |
| DD-03 | Single droplet, no scale path | Cannot serve 10k+ tenants on one box                 | `docker-compose.prod.yml`, `deploy.yml`                      | 6–10 ew | K8s/ECS + managed PG/Redis                | §0.7.3, §3.4.6, EXE-G5 |
| DD-04 | Worker not in prod            | Async billing/notifications never run                | `docker-compose.prod.yml`, `apps/worker/`                    | 1–2 ew  | Add `pcd-worker` + health                 | §0.7.4, §0.1.4         |
| DD-05 | Dispatch stub; FB off prod    | Core loop manual — not orchestration software        | `worker/processors/dispatch.py`, `FLEETBASE_DISPATCH_BRIDGE` | 4–6 ew  | Implement processor + deploy FB           | §0.7.5, §2.2.7         |
| DD-06 | Rate limit fails open         | Abuse + cost runaway when Redis blips                | `platform/rate_limit_middleware.py:82-99`                    | 1 ew    | Fail closed; pooled Redis client          | §0.7.6, §3.5.2–3, B.14 |
| DD-07 | Weak tenant isolation         | Cross-merchant data breach at scale                  | `models.py`, `merchant_models.py`, engines                   | 6–10 ew | Tenant context + RLS/repos + IDOR tests   | §0.7.7, §2.5.1, B.12   |
| DD-08 | No row locks on money path    | Race on concurrent webhooks                          | `confirmation_service.py`, `stripe_webhook_service.py`       | 3–5 ew  | Transactions + `FOR UPDATE` + idempotency | §0.7.8, §2.5.2         |

### High

| ID    | Issue                               | Files                                        | Effort         | Fix                                | Checklist         |
| ----- | ----------------------------------- | -------------------------------------------- | -------------- | ---------------------------------- | ----------------- |
| DD-09 | God-class services (1.6k LOC)       | All major god files split to ≤400 LOC mixins | done dev       | Strangler split ≤400 LOC           | §2.2.1–2.2.14     |
| DD-10 | No CI security scanning             | `.github/workflows/`                         | 1 ew           | Dependabot, CodeQL, Trivy, Bandit  | §2.5.5, B.16      |
| DD-11 | In-process WebSocket hub            | `notification_engine/realtime.py:17`         | 2–3 ew         | Redis pub/sub fanout               | §3.5.1, ARCH-G5   |
| DD-12 | `jwt_secret` dev default            | `config.py`                                  | 0.5 ew         | Fail boot if default in prod       | B.15, §11.1.13    |
| DD-13 | Fleetbase sync unproven at scale    | `fleetbase_engine/retry_queue.py`            | 3–5 ew         | SLO ≥98% + alert + load test       | §3.5.5, §5.1.14   |
| DD-14 | Ad-hoc secrets on droplet           | `deploy.yml`, droplet `.env`                 | 2 ew           | Secret manager + rotation          | §5.1.13, §11.1.14 |
| DD-15 | No API versioning policy            | `routers/`, no CHANGELOG                     | 2–3 ew         | Semver + partner contract tests    | §7.1.4, E.4       |
| DD-16 | Prod ≠ local (FB, Valhalla, worker) | prod vs local compose                        | incl. DD-03–05 | Parity ADR                         | §0.1.5–0.1.6      |
| DD-17 | No load testing                     | none                                         | 3 ew           | k6 + p95 SLO                       | §2.5.4, §5.4      |
| DD-18 | Stripe not proven live in prod      | `stripe_webhook_service.py`                  | 1–2 ew         | Live webhook + reconciliation      | D.9, A.3–A.4      |
| DD-19 | DB no read replica story            | `db.py`, `config.py`                         | 3–4 ew         | Managed PG + replica for analytics | §3.4.7            |
| DD-20 | Model sprawl — no extraction path   | 9 `*_models.py` files                        | 8–12 ew        | Per-context ownership + repos      | §3.2, §0.6.8      |

### Medium

| ID    | Issue                           | Files                          | Effort | Checklist             |
| ----- | ------------------------------- | ------------------------------ | ------ | --------------------- |
| DD-21 | Raw SQL in routers              | 3 router files                 | 1 ew   | §2.2.11               |
| DD-22 | Wildcard `from _deps import *`  | `routers/admin/_deps.py`       | 1 ew   | §2.2.5                |
| DD-23 | Stripe idempotency gaps         | `stripe_webhook_service.py`    | 1–2 ew | §2.5.3, §2.1.14       |
| DD-24 | Unbounded list endpoints        | `*_engine` lists               | 2 ew   | §2.5.6                |
| DD-25 | 61 pointer doc stubs            | `docs/`                        | 1 ew   | E.2                   |
| DD-26 | No Phase 2 feature flags        | `packages/config/`             | 1 ew   | §1.2.4 [x] 2026-07-08 |
| DD-27 | No rolling deploy               | `deploy.yml`                   | 2 ew   | §2.5.7                |
| DD-28 | No backup/restore drill         | Postgres                       | 1 ew   | §5.1.15               |
| DD-29 | No structured logging           | `platform/middleware.py`       | 1–2 ew | B.1–B.2               |
| DD-30 | `route.optimized` catalog drift | `events/catalog.ts`            | 0.5 ew | §3.3.5, §0.6.6        |
| DD-31 | Alembic sprawl policy missing   | `alembic/versions/` (13)       | 0.5 ew | doc only              |
| DD-32 | POD media storage undefined     | `navigation_pod.py`            | 2 ew   | B.17                  |
| DD-33 | SLO/alerting not wired          | `platform/metrics.py`          | 2 ew   | B.3–B.8               |
| DD-34 | Mobile apps not in stores       | `apps/mobile-*/`               | 3 ew   | Appendix C C.6–C.7    |
| DD-35 | No GDPR/PIPEDA export           | privacy API                    | 2–3 ew | §11.1.8–9             |
| DD-36 | No audit log export API         | DomainEvent                    | 2 ew   | §11.1.7               |
| DD-37 | Track pages lack maps           | website/customer track         | 2 ew   | §6.2.3, §0.6.4        |
| DD-38 | Duplicate maps packages         | `packages/maps`, `shared/maps` | 2 ew   | doc ADR               |
| DD-39 | Customer Stripe return URLs     | prod env                       | 0.5 ew | §0.6.5                |
| DD-40 | Lockfile CI missing             | lockfiles                      | 1 ew   | §2.5.8                |

### Low

| ID    | Issue                                      | Files                              | Checklist      |
| ----- | ------------------------------------------ | ---------------------------------- | -------------- |
| DD-41 | Orphan `services/booking.py`               | grep delete                        | §0.6.9, §2.2.8 |
| DD-42 | `admin_engine/support_service` shim        | re-export                          | hygiene        |
| DD-43 | Legacy `FleetbaseIntegrationService` alias | adapter                            | hygiene        |
| DD-44 | Deprecated `services/fleetbase/`           | delete                             | hygiene        |
| DD-45 | Node 20 CI deprecation warnings            | `.github/workflows/` (Node **24**) | hygiene        |
| DD-46 | Hollow `reporting_engine`                  | 2 files                            | §3.2.12        |
| DD-47 | README vs 447 routes                       | `apps/api/README.md`               | E.3            |
| DD-48 | Conflicting mobile readiness %             | `MODULE_SCORECARD.md`              | E.2            |
| DD-49 | CONTRIBUTING not enforced                  | PR template                        | §0.3.5         |
| DD-50 | Inconsistent error JSON                    | `routers/`                         | §2.2.12        |

### Diligence gate

- [ ] **DD-G1:** All **Critical** (DD-01–DD-08) checked — required for Series A technical sign-off
- [ ] **DD-G2:** All **High** (DD-09–DD-20) checked or accepted with escrow milestones
- [ ] **DD-G3:** External CTO review — 0 open Critical findings
- [ ] **DD-G4:** Load test proves p95 latency SLO at 10× current peak traffic

---

## Appendix G — Master verification commands

```bash
# Foundation
pnpm validate:p0 && pnpm validate:p0:prod
pnpm validate:d2 && pnpm validate:d3 && pnpm validate:d3:e2e && pnpm validate:d3:prod
pnpm fleetbase:replay
pnpm docker:fleetbase:verify

# Health
curl -s https://api.porterchain.com/health/ready | python3 -m json.tool
curl -s http://localhost:8001/health/ready | python3 -m json.tool

# Fleetbase sync (admin auth)
curl -s http://localhost:8001/v1/admin/diagnostics/fleetbase-sync | python3 -m json.tool

# Schema
cd apps/api && alembic current

# Architecture grep audits
rg "localhost:8000" apps/ website/ --glob '!**/*.md'
rg "from.*admin_engine" apps/api/src/porterchain_api/merchant_engine/

# Format
pnpm format:check

# Due diligence audits (July 2026 baseline)
find apps/api/tests -name 'test_*.py' | wc -l          # expect ≥20 (DD-01) — currently 27
find apps website packages shared -name '*.test.*' 2>/dev/null | grep -v node_modules | wc -l  # expect >0
rg -l 'execute\(|text\(' apps/api/src/porterchain_api/routers  # expect 0 (DD-21)
rg -c 'with_for_update|begin_nested|SELECT FOR UPDATE' apps/api/src/porterchain_api  # expect >0 after DD-08
rg -il 'sentry|datadog|opentelemetry' apps/api/src  # expect hits after DD-02
rg 'worker' infrastructure/deploy/docker-compose.prod.yml  # expect match after DD-04
wc -l apps/api/src/porterchain_api/collaboration_engine/crm_service.py  # target ≤400 after DD-09
```

---

## Execution waves (Fowler sequencing)

| Wave   |    Weeks | Sections                                      | Unlocks                     |
| ------ | -------: | --------------------------------------------- | --------------------------- |
| **DD** | **8–12** | **Appendix H DD-01–DD-08 (Critical)**         | **Series A technical pass** |
| 0      |      2–4 | §0, Appendix A prod column                    | Foundation, Execution 7+    |
| 1      |      4–6 | §2 tests, §5 worker, Appendix B observability | Engineering 8+              |
| 2      |        4 | §1, §6 reposition + maps                      | Product + Design 8+         |
| 3      |     8–12 | §3 strangler + DD-09–DD-20 High               | Architecture 9+             |
| 4      |        8 | §8 vertical depth                             | Moat 7+                     |
| 5      |    12–16 | §4 ETA, §7 Shopify                            | AI + Platform 8+            |
| 6      |  6–12 mo | §9–§11 metrics, SOC2, SAML                    | Investor + Enterprise 9+    |

**10/10 all dimensions:** 18–24 months disciplined execution.

---

## Related documents

| Document                                                                        | Role                        |
| ------------------------------------------------------------------------------- | --------------------------- |
| [masterrule.md](../masterrule.md)                                               | Architecture SSOT           |
| [CTO_AUDIT_REPORT.md](../CTO_AUDIT_REPORT.md)                                   | Open issues O-01–O-11       |
| Appendix H (this doc)                                                           | DD-01–50 diligence register |
| [RUNBOOK.md](../RUNBOOK.md)                                                     | Ops                         |
| [DOMAIN_MODEL.md](../DOMAIN_MODEL.md)                                           | Aggregates                  |
| [docs/architecture/SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) | Topology                    |

## Governance

- **Owner:** CTO / founder
- **Review:** Monthly gates; quarterly §12 score table
- **New items:** Require ADR if Phase 2 surface
- **Never:** Rebuild; microservice split; Fleetbase bypass; CRM before prod dispatch
