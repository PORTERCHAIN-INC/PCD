# PorterChain — master development test cases (**ENTRY SSOT**)

**Status:** living catalog for local/CI development (not prod Doppler alone).  
**Role:** **Start here.** This file is the index + P0 handshake + cross-cutting matrices. Deep persona/integration catalogs live in siblings below — do not fork a fourth “master.”  
**Mapped:** 2026-09-17 via **Graphify** (`query` / `god-nodes` / `path` / `explain`) + `ARCHITECTURE.md` + OpenAPI (**568 paths / 639 ops**) + portal inventory.  
**Sensors completed (sequential moments — never parallel):**

| Moment | Tool                                       | What landed in this catalog                                                                                  |
| ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------ |
| A      | Graphify CLI                               | Trunk map, god nodes, page census, HS-01…24                                                                  |
| B      | CodeGraph CLI `explore`                    | MapsService `route_with_source` → `_valhalla_*` / `_osrm_*`; `OrchestratorOpsService` ↔ adapter orchestrator |
| C      | Ripwire `--for` / `--expand` / `--callers` | `TEST_CATALOG` / `CHAOS_SCENARIOS` / `_probe_vroom` / `integration_health`; HS-25 · MAP-11                   |

**Deep slice (separate session):** [MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md](MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md) — Google Places/tiles · FCM · browser/mobile push · notification_engine · indirect Fleetbase→notify · Ripwire GAP board (`registerBrowserPush` untested, etc.).

**Do not** run Graphify + CodeGraph + Ripwire in the same session.

**Policy holds (not bugs):** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md).  
**Integrations SSOT:** [INTEGRATIONS.md](../INTEGRATIONS.md) · `integrations.yaml` · `pnpm validate:integrations-matrix`.  
**Existing seed:** ~231 `apps/api/tests/test_*.py` + `scripts/verify_*.py` + `pnpm validate:*` — expand gaps; link cases to seeds.

**Charter gate:** Prefer revenue, trust, utilization, identity, quote→book→dispatch→POD→invoice. Never rebuild Fleetbase dispatch / Google routing / Phase-3-as-SKU.

### Catalog family (who owns what)

| Doc                                                                                            | Owns                                                                                                       | Use when                     |
| ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------- |
| **This file**                                                                                  | Index, P0 `HS-*`, cross-cutting API/ENG/MAP/FB/PAY/NOTIF/INT/DB/DOC/WRK/ARCH                               | First open / CI planning     |
| [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md)                 | Fleetbase adapter modules, Valhalla/OSRM/VROOM, Clerk/Stripe/FCM/Shopify/ERP, DIAG probes                  | Handshakes & vendor leaves   |
| [MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md](MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md)       | Google Places/tiles · FCM · browser/mobile push · notification_engine · **indirect** FB→notify · GAP board | Maps + Firebase + push depth |
| [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md)                                   | Compose→spatial→UI heatmap + load                                                                          | Full-stack soak checklist    |
| [DEVELOPMENT_TEST_CASES_CATALOG.md](DEVELOPMENT_TEST_CASES_CATALOG.md)                         | VROOM spine depth + missed-surfaces table                                                                  | Optimize / VROOM regression  |
| [ADMIN_SUPERADMIN_DEV_TESTCASES.md](ADMIN_SUPERADMIN_DEV_TESTCASES.md)                         | Admin pages, settings, RBAC, Test Center                                                                   | Staff persona                |
| [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)                     | Merchant portal + admin merchant 360                                                                       | Merchant persona             |
| [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)                       | Customer portal + retail book/track                                                                        | Customer persona             |
| [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md)                               | Driver web + admin drivers (pointer to mobile depth)                                                       | Driver web / admin           |
| [MOBILE_DRIVER_DEV_TEST_CASES.md](MOBILE_DRIVER_DEV_TEST_CASES.md)                             | Expo `mobile-driver` screens/files/API/Fleetbase/Maps/FCM/COD                                              | Driver mobile depth          |
| [WEBSITE_PERSONA_DEV_TEST_CASES.md](WEBSITE_PERSONA_DEV_TEST_CASES.md)                         | Website `:3000` GTM + quote/book/track + SEO leaves                                                        | Website / GTM                |
| [CODEGRAPH_QUOTE_VISITOR_OPTIMIZE_SCHEMAS.md](CODEGRAPH_QUOTE_VISITOR_OPTIMIZE_SCHEMAS.md)     | Field contracts for Quote/Visitor/Optimize (+ `test_hs_wui_mprte_codegraph_p0.py`)                         | Assert shapes before e2e     |
| [RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md](RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md)                         | Thin-router/handoff blast + website Playwright map                                                         | Moment C · `website/e2e`     |
| [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)                   | OptimizePanel / orchestrator / Maps                                                                        | Capacity utilization         |
| [SHOPIFY_MERCHANT_CONNECTION_DEV_TEST_CASES.md](SHOPIFY_MERCHANT_CONNECTION_DEV_TEST_CASES.md) | Shopify OAuth / carrier / ingest                                                                           | Shopify slice                |
| [PLATFORM_DEV_TEST_CASES.md](PLATFORM_DEV_TEST_CASES.md)                                       | **POINTER only** (redirects here)                                                                          | Do not grow                  |

### Live census (Graphify + tree)

| Surface                           |                                                                       Count |
| --------------------------------- | --------------------------------------------------------------------------: |
| OpenAPI paths / ops               |                                                                   568 / 639 |
| Admin `page.tsx`                  |                                                                          37 |
| Merchant `page.tsx`               |                                                                          22 |
| Driver web `page.tsx`             |                                                                          20 |
| Customer `page.tsx`               |                                                                          11 |
| Website `page.tsx`                |                                                                         ~77 |
| ORM model files / classes         |                                                      12 files / ~80 classes |
| Engines (`*_engine`)              |                                                                          16 |
| Diagnostics `TEST_CATALOG` probes |                                                                          30 |
| Compose core leaves               |      Postgres · Redis · SpiceDB · Mailpit · Valhalla · OSRM · VROOM · proxy |
| Fleetbase override leaves         | MySQL · Valkey · socket · scheduler · queue · console · application · httpd |

---

## 0. ID scheme & layers

| Prefix                | Layer                                                                 |
| --------------------- | --------------------------------------------------------------------- |
| `HS-*`                | Cross-system **handshakes** (dev smoke that must green before UI)     |
| `API-*`               | FastAPI personas (`/v1/*`, `/driver-api/v1/*`, webhooks)              |
| `ENG-*`               | `*_engine` unit / service                                             |
| `FB-*`                | Fleetbase adapter + sync + VROOM (via adapter only)                   |
| `MAP-*`               | Valhalla / OSRM / MapsService / Google Places+tiles                   |
| `AUTH-*`              | Clerk / Staff IdP / SpiceDB / API keys / OAuth                        |
| `PAY-*`               | Stripe Checkout / Connect COD / webhooks / ledger                     |
| `NOTIF-*`             | notification_engine / FCM / email / Mailpit / inbox                   |
| `INT-*`               | Shopify / WooCommerce / NetSuite / Zapier / partner ERP / lead ingest |
| `UI-A-*`              | Admin portal `:3002` pages + sub-surfaces                             |
| `UI-M-*`              | Merchant portal `:3001`                                               |
| `UI-C-*`              | Customer portal `:3004`                                               |
| `UI-D-*`              | Driver web `:3003` (+ BFF)                                            |
| `UI-W-*`              | Website `:3000`                                                       |
| `MOB-D-*` / `MOB-C-*` | Expo driver / customer                                                |
| `DB-*`                | Postgres models / Alembic / ownership / constraints                   |
| `DOC-*`               | Docker / compose / ports / health / Valkey                            |
| `WRK-*`               | Worker / EventBus / DLQ / idempotency                                 |
| `ARCH-*`              | Architecture contracts / OpenAPI census / D2 / vendor leaves          |
| `UX-*`                | A11y / pagination / design copy / tablet / i18n                       |

**Priority:** P0 = ship-blocker / money-trust · P1 = core loop · P2 = regression/polish · P3 = Phase2+ / intentional depth holds.

Each case: **ID · Prio · Precondition → Steps → Expected · Seed/guard**.

---

## 1. Surface inventory (SSOT)

### 1.1 HTTP personas (ARCHITECTURE leaf — Wave 3)

| Persona           | Prefix                                                 | Auth                                               | Ops (tag approx)               |
| ----------------- | ------------------------------------------------------ | -------------------------------------------------- | ------------------------------ |
| Staff             | `/v1/admin`                                            | Staff IdP (`pc_staff_sid` / `Bearer staff_sess_*`) | ~138 `admin` + ops/diagnostics |
| Merchant portal   | `/v1/merchant`                                         | Clerk org                                          | ~179 `merchant`                |
| Partner API       | `/v1/merchant-api`                                     | API key + idempotency                              | ~7                             |
| Driver mobile/API | `/driver-api/v1`                                       | Clerk Bearer                                       | ~77 `driver`                   |
| Retail book       | `/v1/quotes` `/v1/bookings`                            | session / checkout                                 | quotes/bookings                |
| Public track      | `/v1/orders/{tracking_number}`                         | none                                               | public                         |
| Vendors           | `/webhooks/clerk\|stripe\|fleetbase\|checkr\|shopify…` | signatures                                         | webhooks                       |

**Cut (must stay gone):** `POST /driver/location`, `GET /v1/merchant/tracking/orders/{id}`, `POST .../invoices/{id}/resend`. Guard: `scripts/openapi_census.py`.

### 1.2 Engines (16)

`admin_engine` · `analytics_engine` · `billing_engine` · `booking_engine` · `collaboration_engine` · `compliance_engine` · `driver_engine` · `fleetbase_engine` · `gateway_engine` · `intelligence_engine` · `merchant_engine` · `notification_engine` · `oauth_engine` · `order_engine` · `pricing_engine` · `support_engine`

### 1.3 Microservices / leaves

| Leaf                              | Port / host  | Owns                                      | Must not                           |
| --------------------------------- | ------------ | ----------------------------------------- | ---------------------------------- |
| FastAPI                           | `:8001`      | Commercial + domain                       | Fleetbase HTTP from browsers       |
| Worker                            | process      | EventBus drain + FB retry + Shopify queue | Inline UI                          |
| Fleetbase + adapter               | `:8000`      | Dispatch, GPS SoT, POD, VROOM             | Rebuilt in `*_engine`              |
| Valhalla                          | `:8002`      | Route/matrix/isochrone/costing            | —                                  |
| OSRM                              | `:5000`      | Fallback ETA/distance (GTA ±150 km)       | Public demo as default             |
| Postgres 18                       | compose      | ORM                                       | SQLite                             |
| Redis 8.8                         | compose      | cache/sessions/bus                        | —                                  |
| Fleetbase Valkey 8                | override     | FB cache                                  | upstream redis:4                   |
| Mailpit                           | compose      | Dev SMTP                                  | Mailhog                            |
| Stripe                            | external     | Checkout + COD Connect                    | Import outside `sdk.py`            |
| Clerk                             | external     | Identity (portal triad)                   | Firebase Auth                      |
| Firebase FCM                      | external     | Push only                                 | Login/RBAC                         |
| Google Maps                       | Places+tiles | Autocomplete / map render                 | Distance/ETA/matrix                |
| SpiceDB                           | Check        | AuthZ                                     | Cached allows                      |
| Shopify / Woo / NetSuite / Zapier | INT          | Connectors                                | Admin minting Shopify for merchant |

### 1.4 Admin pages (`apps/admin` — 37 routes)

`/sign-in` · `/activate-staff` · `/dashboard` · `/operations` · `/orders` · `/orders/[id]` · `/merchants` · `/merchants/[id]` · `/drivers` · `/drivers/[id]` · `/customers` · `/customers/[id]` · `/leads` · `/leads/[id]` · `/leads/pipeline` · `/leads/calendar` · `/finance` · `/finance/invoices/[id]` · `/pricing` · `/booking-drafts` · `/booking-drafts/[id]` · `/claims` · `/claims/[id]` · `/support` · `/support/[id]` · `/inbox` · `/notifications` · `/blog` · `/blog/new` · `/blog/[id]` · `/settings` · `/account/security` · `/system` · `/system-health` · `/system-tests` · aliases under `/admin/*`

**Merchant detail sub-surfaces (operate one company):** Overview · Billing · Pricing · Locations · Standing orders · Settings · related AR/finance panels.

### 1.5 Merchant pages (`apps/merchant-portal` — 22)

`/sign-in` · `/sign-up` · `/onboarding` · `/dashboard` · `/book` · `/bulk` · `/orders` · `/orders/[order_id]` · `/routes` · `/routes/[job_id]` · `/track` · `/billing` · `/billing/invoices/[invoice_id]` · `/team` · `/settings` · `/shopify` · `/api` · `/reports` · `/referrals` · `/notifications` · `/help`

### 1.6 Customer pages (`apps/customer` — 11)

See [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md) §1.1.

### 1.7 Driver web (`apps/driver-portal` — 20)

`/login` · `/onboarding` · `/dashboard` · `/jobs` · `/jobs/[orderId]` · `/stops` · `/navigation` · `/shift` · `/wallet` · `/earnings` · `/performance` · `/documents` · `/vehicle` · `/insurance` · `/profile` · `/communications` · `/support` · `/training` · `/emergency` — **BFF** `/api/driver` → `/driver-api/v1` (do not unify with mobile Bearer).

### 1.8 Website (`website/` — ~77 `page.tsx`)

Home · quote/book/track · solutions/industry/city · vehicles · trust/* · developers · blog · SEO landings · login handoff. Marketing validators: `pnpm validate:product-vision` · `validate:website-seo`.

### 1.9 Mobile

| App           | Screens (current)                                                                                  | API                                               |
| ------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Driver Expo   | SignIn, Onboarding, Jobs, JobDetail, Route, Docs, Money, Inbox, Support, More, Invite, ForceUpdate | `/driver-api/v1` + FCM + handshake                |
| Customer Expo | SignIn, Track                                                                                      | public track + Clerk — **depth intentional skip** |

---

## 2. P0 handshake matrix (run first on localhost)

| ID    | Prio | Handshake                  | Steps                                                                                                 | Expected                                                                                                                | Seed/guard                                              |
| ----- | ---- | -------------------------- | ----------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| HS-01 | P0   | API readiness              | `GET :8001/health` (+ readiness)                                                                      | 200; Valhalla/OSRM reachability flags honest                                                                            | `test_health.py`, diagnostics probes                    |
| HS-02 | P0   | Postgres                   | `pnpm db:test` / smoke                                                                                | connect + alembic head                                                                                                  | `test_postgres_smoke.py`, `verify_alembic_head.py`      |
| HS-03 | P0   | Redis                      | ping via shared client                                                                                | PONG                                                                                                                    | compose + worker                                        |
| HS-04 | P0   | Clerk triad sync           | `pnpm clerk:sync`; API has `CLERK_<PORTAL>_*`                                                         | no ad-hoc `ADMIN_CLERK_*`                                                                                               | `test_clerk_registry.py`                                |
| HS-05 | P0   | Staff IdP session          | staff login → cookie → `/v1/admin/me`                                                                 | 200; bypass only when `CLERK_DEV_BYPASS` + `APP_ENV` allow                                                              | auth tests                                              |
| HS-06 | P0   | Merchant Clerk → API       | portal Bearer → `/v1/merchant/session`                                                                | org context                                                                                                             | merchant RBAC tests                                     |
| HS-07 | P0   | Driver Bearer → API        | `/driver-api/v1/...`                                                                                  | 401 without token; 200 with                                                                                             | driver auth                                             |
| HS-08 | P0   | Driver web BFF             | browser → `:3003/api/driver/*` → `:8001`                                                              | never calls `:8000`                                                                                                     | mobile/portal smoke                                     |
| HS-09 | P0   | MapsService Valhalla-first | quote distance                                                                                        | source=valhalla (or osrm fallback labeled)                                                                              | `test_valhalla_costing`, routing tests                  |
| HS-10 | P0   | OSRM local fallback        | stop Valhalla; quote still works                                                                      | osrm `:5000`; public demo **off**                                                                                       | `verify_architecture` / maps                            |
| HS-11 | P0   | Fleetbase adapter          | adapter health + sync enqueue                                                                         | RetryQueue accepts; no portal→FB HTTP                                                                                   | `test_fleetbase_*`                                      |
| HS-12 | P0   | Fleetbase webhook          | signed webhook → status translate                                                                     | Order state updates; idempotent                                                                                         | `test_fleetbase_webhook_retry.py`                       |
| HS-13 | P0   | VROOM via adapter only     | optimize/orchestrator ops                                                                             | no `*_engine` VROOM import                                                                                              | `verify_vendor_leaves`, `test_orchestrator_ops.py`      |
| HS-14 | P0   | Stripe Checkout            | retail book → Checkout session                                                                        | webhook idempotent settle                                                                                               | stripe + booking tests                                  |
| HS-15 | P0   | Stripe COD Connect         | COD issue checkout/link                                                                               | additive; Checkout path unbroken                                                                                        | `billing_engine` COD                                    |
| HS-16 | P0   | FCM token register         | admin/driver/customer register device                                                                 | token stored; push only (not Auth)                                                                                      | notification phase tests                                |
| HS-17 | P0   | Email / Mailpit            | trigger booking email                                                                                 | appears in Mailpit; not Mailhog                                                                                         | SMTP env                                                |
| HS-18 | P0   | EventBus → worker          | publish domain event                                                                                  | worker handler runs; DLQ on poison                                                                                      | event catalog parity                                    |
| HS-19 | P0   | Shopify webhook queue      | shopify webhook → worker `process_queued_webhook`                                                     | create/cancel shipment path                                                                                             | shopify_service                                         |
| HS-20 | P0   | Google Places only         | address autocomplete in book UI                                                                       | Places OK; **no** Distance Matrix for pricing                                                                           | `verify_no_ops_spatial_math`                            |
| HS-21 | P0   | Partner API key            | `/v1/merchant-api` book with key + idempotency-key                                                    | replay safe                                                                                                             | `test_merchant_api_idempotency.py`                      |
| HS-22 | P0   | Mobile handshake probe     | driver app handshake types                                                                            | `:8001` only; no `:8000`/SocketCluster                                                                                  | `validate:mobile-smoke`                                 |
| HS-23 | P0   | OpenAPI census             | `pnpm validate:architecture` census                                                                   | 639 classified; no new untagged business paths                                                                          | `openapi_census.py`                                     |
| HS-24 | P0   | Project mode immutable     | `POST .../project-mode`                                                                               | always 403 `project_mode_immutable`                                                                                     | intentional skip / settings                             |
| HS-25 | P0   | OSRM ⊥ Optimize            | **stop OSRM only**; Valhalla + VROOM up; Admin Optimize enqueue/run                                   | Optimize still succeeds (`VROOM_ROUTER=valhalla`); quotes may stay Valhalla-primary — proves **no OSRM→Fleetbase edge** | CodeGraph path + `_probe_vroom`; `ROUTE_OPTIMIZATION_*` |
| HS-26 | P0   | Diagnostics catalog live   | Admin `/system-tests` runs each `TEST_CATALOG` id (clerk…scheduled_jobs)                              | pass/warn/skip honest; VROOM never probed as PC HTTP port                                                               | `diagnostics_catalog.py`, Ripwire                       |
| HS-27 | P1   | Chaos matrix               | Inject `CHAOS_SCENARIOS` / `FAILURE_SCENARIOS` (osrm_failure, valhalla_failure, fleetbase_offline, …) | degrade closed; UI shows statusTone; no stack dump                                                                      | admin `diagnostics.ts`, e2e catalog                     |

---

## 3. API / FastAPI (persona suites)

### 3.1 Auth & identity — `AUTH-*`

| ID      | P   | Case                                       | Expected                        | Seed                        |
| ------- | --- | ------------------------------------------ | ------------------------------- | --------------------------- |
| AUTH-01 | P0  | Invalid JWT all personas                   | 401 envelope                    | `test_error_envelope.py`    |
| AUTH-02 | P0  | Cross-portal token (merchant JWT on admin) | 401/403                         | clerk registry              |
| AUTH-03 | P0  | Staff passkey/magic + Redis session        | session binds AdminUser         | staff IdP                   |
| AUTH-04 | P0  | SpiceDB Check deny                         | module gated 403                | `test_hybrid_rbac.py`       |
| AUTH-05 | P0  | IDOR order/customer/merchant               | 404/403 not leak                | `test_idor.py`              |
| AUTH-06 | P1  | Merchant onboarding provision              | company file + seat             | onboarding tests            |
| AUTH-07 | P1  | Customer onboarding                        | Customer row + Clerk link       | customer persona doc        |
| AUTH-08 | P1  | Driver invite existing                     | InvitationService path          | drivers_admin               |
| AUTH-09 | P1  | OAuth third-party clients                  | list/create/revoke              | `test_oauth_service.py`     |
| AUTH-10 | P1  | API key rotate/revoke                      | partner calls fail after revoke | merchant-api                |
| AUTH-11 | P2  | Clerk webhook user sync                    | identity links upsert           | clerk webhooks              |
| AUTH-12 | P2  | Dev bypass only in allowed APP_ENV         | prod reject Bearer `dev`        | `test_config_production.py` |

### 3.2 Quotes / bookings / public track — `API-B-*`

| ID       | P   | Case                             | Expected                       | Seed                    |
| -------- | --- | -------------------------------- | ------------------------------ | ----------------------- |
| API-B-01 | P0  | Quote in GTA                     | cents + distance source        | booking loop            |
| API-B-02 | P0  | Quote outside extract            | clear coverage error           | FSA/coverage            |
| API-B-03 | P0  | Book → Order                     | state machine legal transition | `test_dod_quote_book_*` |
| API-B-04 | P0  | Public track by tracking #       | snapshot; no PII leak          | public track            |
| API-B-05 | P1  | Booking draft admin promote      | draft→order audit              | booking drafts          |
| API-B-06 | P1  | Multi-stop quote                 | route_multi / package spine    | labels/packages         |
| API-B-07 | P1  | Cancel/duplicate merchant-owned  | ownership enforced             | merchant cancel         |
| API-B-08 | P2  | Visitor session website→customer | handoff preserves quote        | visitor session         |

### 3.3 Merchant portal API — `API-M-*`

| ID       | P   | Case                       | Expected                       | Seed                       |
| -------- | --- | -------------------------- | ------------------------------ | -------------------------- |
| API-M-01 | P0  | `/session` `/me`           | MerchantContext                | profile_team               |
| API-M-02 | P0  | Book delivery idempotent   | same key → same order          | portal idempotency         |
| API-M-03 | P0  | Orders list pagination     | cursor/page contract           | `validate:pagination`      |
| API-M-04 | P1  | Bulk CSV upload            | job + errors                   | route CSV                  |
| API-M-05 | P1  | Route import optimize      | Maps sequence; no engine VROOM | import optimize            |
| API-M-06 | P1  | Team seats + CRM sync      | seat mutations sync contacts   | team_service               |
| API-M-07 | P1  | Billing invoices/credits   | cents integrity                | merchant billing pack      |
| API-M-08 | P1  | Privacy DSR export/delete  | GDPR path                      | `test_merchant_privacy.py` |
| API-M-09 | P1  | Webhook delivery outbound  | signed retries                 | webhook_delivery           |
| API-M-10 | P2  | Referrals credits          | ledger rows                    | referrals                  |
| API-M-11 | P2  | Reports spend/destinations | merchant-scoped only           | reports                    |
| API-M-12 | P2  | Branding/tax/documents     | settings surface               | branding/tax               |

### 3.4 Admin API — `API-A-*`

| ID       | P   | Case                                   | Expected                                   | Seed                       |
| -------- | --- | -------------------------------------- | ------------------------------------------ | -------------------------- |
| API-A-01 | P0  | `require_module` matrix                | each module 403 without                    | RBAC                       |
| API-A-02 | P0  | Control Tower assign/score             | scoring; no custom GPS SoT                 | CT / assignment            |
| API-A-03 | P0  | Orders 360 + assist decide             | propose→confirm only                       | order assist               |
| API-A-04 | P0  | Finance invoice generate/PDF           | cents; PDF 404 when missing                | invoice tests              |
| API-A-05 | P0  | Merchant lifecycle close/reopen        | **never hard DELETE**                      | lifecycle                  |
| API-A-06 | P1  | Driver 360 + verification badges       | Identity/Checkr/abstract sources           | driver verification        |
| API-A-07 | P1  | Leads pipeline/ingest bus              | channel adapters                           | lead_* tests               |
| API-A-08 | P1  | Settings write + audit restore         | writable keys only; project mode immutable | settings                   |
| API-A-09 | P1  | Diagnostics probes                     | honest downed leaf                         | diagnostics                |
| API-A-10 | P1  | Notifications admin + sandbox AI usage | role matrix fanout                         | notification_role_matrix   |
| API-A-11 | P1  | Claims/support tickets                 | support_engine ownership                   | claims                     |
| API-A-12 | P2  | Blog CMS media                         | admin blog                                 | blog_service               |
| API-A-13 | P2  | Investor/platform metrics              | cadence                                    | monopoly/investor          |
| API-A-14 | P2  | FSA/GTA150 admin rates                 | coverage                                   | `test_fsa_admin_gta150.py` |

### 3.5 Driver API — `API-D-*`

| ID       | P   | Case                              | Expected                     | Seed                                |
| -------- | --- | --------------------------------- | ---------------------------- | ----------------------------------- |
| API-D-01 | P0  | List assigned jobs                | only assigned                | driver jobs                         |
| API-D-02 | P0  | Status transitions                | legal only                   | status translator                   |
| API-D-03 | P0  | POD / scan gate                   | QR parse via ScanGateService | d3 POD contract                     |
| API-D-04 | P1  | COD checkout issue                | StripeCodService path        | COD                                 |
| API-D-05 | P1  | Wallet ledger read                | driver_engine ledger         | wallet                              |
| API-D-06 | P1  | Docs upload helper                | verification flags           | compliance                          |
| API-D-07 | P2  | Offline optimize route            | labeled offline path         | offline optimize                    |
| API-D-08 | P0  | No GPS POST to PorterChain as SoT | Fleetbase owns GPS           | intentional skip / GPS ingest waves |

### 3.6 Partner / gateway / webhooks — `API-P-*`

| ID       | P   | Case                                         | Expected               | Seed                                      |
| -------- | --- | -------------------------------------------- | ---------------------- | ----------------------------------------- |
| API-P-01 | P0  | merchant-api idempotency                     | replay                 | merchant_api_idempotency                  |
| API-P-02 | P0  | Rate limit gateway                           | 429 envelope           | `test_gateway_rate_limit.py`              |
| API-P-03 | P0  | Stripe webhook signature + idempotency table | no double settle       | `verify_stripe_webhook_idempotency_table` |
| API-P-04 | P0  | Fleetbase webhook signature                  | reject bad sig         | fleetbase webhook                         |
| API-P-05 | P1  | Clerk webhook                                | user events            | —                                         |
| API-P-06 | P1  | Checkr webhook                               | background status      | driver_background                         |
| API-P-07 | P1  | Shopify HMAC                                 | reject bad; queue good | shopify                                   |
| API-P-08 | P2  | Lead channel webhooks (Meta/CAPI etc.)       | ingest bus             | lead_channel                              |

---

## 4. Engines & domain — `ENG-*`

| ID     | P   | Engine focus           | Case                                          | Expected                    |
| ------ | --- | ---------------------- | --------------------------------------------- | --------------------------- |
| ENG-01 | P0  | booking                | OrderState transitions                        | illegal transition rejected |
| ENG-02 | P0  | pricing                | Quote bridge == SQLAlchemy repo               | parity tests                |
| ENG-03 | P0  | billing                | Ledger cents; COD policy ≠ SDK                | sdk isolation               |
| ENG-04 | P0  | fleetbase              | BookingSync + RetryQueue SLO                  | sync health                 |
| ENG-05 | P0  | merchant               | Org SSOT admin↔portal same file               | merchant_org_ssot           |
| ENG-06 | P1  | admin CT               | Scoring weights stable                        | assignment_scoring          |
| ENG-07 | P1  | notification           | Role fanout DRIVER_ASSIGNED                   | role_matrix                 |
| ENG-08 | P1  | collaboration          | Lead merge/score/nurture                      | lead_*                      |
| ENG-09 | P1  | support                | Claims ownership of admin_models writes       | claims                      |
| ENG-10 | P1  | driver                 | Façade over Fleetbase; wallet_ledger writes   | driver invert               |
| ENG-11 | P1  | compliance             | Expiry sweep revoke                           | abstract/expiry             |
| ENG-12 | P1  | gateway                | Usage logs via merchant_engine                | gateway                     |
| ENG-13 | P1  | oauth                  | Client list payload                           | oauth                       |
| ENG-14 | P2  | order                  | platform_detail composition                   | order 360                   |
| ENG-15 | P3  | analytics/intelligence | Scaffold + PHASE2_BOUNDARY only               | intelligence boundary       |
| ENG-16 | P0  | D2 freeze              | No new cross-engine imports outside allowlist | `validate:d2`               |

---

## 5. Spatial stack — `MAP-*` / VROOM

| ID     | P   | Case                                                       | Expected                                                       | Guard                                               |
| ------ | --- | ---------------------------------------------------------- | -------------------------------------------------------------- | --------------------------------------------------- |
| MAP-01 | P0  | Valhalla route/matrix/isochrone via MapsService public API | engines never call `_valhalla_*`                               | MapsService                                         |
| MAP-02 | P0  | OSRM fallback when Valhalla down                           | labeled source                                                 | —                                                   |
| MAP-03 | P0  | Public OSRM demo default false                             | CI fails unlabeled public OSRM                                 | architecture                                        |
| MAP-04 | P0  | Google not used for pricing distance                       | Places/tiles only                                              | fleetbase-first                                     |
| MAP-05 | P0  | No haversine in admin_engine ops                           | only labeled UI approx                                         | `verify_no_ops_spatial_math`                        |
| MAP-06 | P1  | Vehicle class costing (box vs auto)                        | costing selector                                               | `test_valhalla_costing`                             |
| MAP-07 | P1  | GTA ±150 km extract only                                   | outside → coverage fail                                        | FSA                                                 |
| MAP-08 | P0  | VROOM only in fleetbase-adapter orchestrator               | no PC VROOM client                                             | vendor leaves                                       |
| MAP-09 | P1  | Optimize panel / orchestrator ops                          | assignments validated in service                               | operations                                          |
| MAP-10 | P3  | Live traffic SoT                                           | **intentional skip** — Valhalla `date_time` optional only      | skips doc                                           |
| MAP-11 | P0  | Architecture: no directed `OSRM → FleetbaseClient`         | Pricing/ETA = MapsService; TSP = Fleetbase VROOM→Valhalla only | Graphify `path` (undirected only via scoring tests) |
| MAP-12 | P0  | `_routing_health`                                          | Valhalla `/status` preferred else OSRM route probe             | `platform/health.py`, `test_health.py`              |
| MAP-13 | P1  | Compose `VROOM_ROUTER=valhalla`                            | VROOM must not default to OSRM matrix                          | `docker-compose.yml` profile `routing`              |

---

## 6. Fleetbase — `FB-*`

| ID    | P   | Case                                        | Expected                                   |
| ----- | --- | ------------------------------------------- | ------------------------------------------ |
| FB-01 | P0  | Adapter client errors mapped                | ErrorHandler                               |
| FB-02 | P0  | Sync enqueue on book                        | RetryQueue depth visible in ops            |
| FB-03 | P0  | Webhook status translate                    | StatusTranslator                           |
| FB-04 | P0  | TrackingFacade snapshot for public/merchant | no SocketCluster in web                    |
| FB-05 | P1  | Replay sync script safe                     | `scripts/replay_fleetbase_sync.py` dry-run |
| FB-06 | P1  | Console link only from admin system-links   | portals never embed `:8000` UI             |
| FB-07 | P1  | Driver online SoT = Fleetbase               | PC does not invent online store            |
| FB-08 | P2  | POD media path                              | `validate:pod-media`                       |
| FB-09 | P3  | HOS/break → VROOM OrderConfig               | intentional hold                           |

---

## 7. Money — `PAY-*`

| ID     | P   | Case                                                     | Expected                          |
| ------ | --- | -------------------------------------------------------- | --------------------------------- |
| PAY-01 | P0  | Checkout success webhook                                 | order paid once                   |
| PAY-02 | P0  | Webhook replay                                           | idempotent                        |
| PAY-03 | P0  | Only `porterchain_services/stripe/sdk.py` imports stripe | allowlist                         |
| PAY-04 | P0  | COD Connect additive                                     | Checkout unbroken                 |
| PAY-05 | P1  | Invoice PDF/CSV cents                                    | no float drift                    |
| PAY-06 | P1  | Merchant AR one total                                    | BD tests                          |
| PAY-07 | P1  | Credit notes / wallet package                            | billing_engine                    |
| PAY-08 | P1  | Driver payout mark via admin_engine                      | ledger in driver_engine           |
| PAY-09 | P2  | Remind/pay link                                          | invoice remind                    |
| PAY-10 | P2  | Customer Stripe return URLs                              | `validate:customer-stripe-return` |

---

## 8. Notifications — `NOTIF-*`

| ID       | P   | Case                          | Expected                       |
| -------- | --- | ----------------------------- | ------------------------------ |
| NOTIF-01 | P0  | Event → role fanout matrix    | customer/merchant/driver/admin |
| NOTIF-02 | P0  | FCM send (sandbox/mock)       | no Auth confusion              |
| NOTIF-03 | P0  | Email via SMTP → Mailpit      | rendered                       |
| NOTIF-04 | P1  | Admin inbox realtime WS token | BFF cookie path                |
| NOTIF-05 | P1  | Quiet hours / prefs           | merchant alert prefs           |
| NOTIF-06 | P1  | SLI metrics                   | notification_sli               |
| NOTIF-07 | P1  | Processor drain               | notifications_processor        |
| NOTIF-08 | P2  | Loud push ops                 | ops loud push                  |
| NOTIF-09 | P2  | AI gap-fill comms (flagged)   | propose only                   |

---

## 9. Integrations / ERP — `INT-*`

| ID     | P   | Integration                   | Case                                             | Expected                       |
| ------ | --- | ----------------------------- | ------------------------------------------------ | ------------------------------ |
| INT-01 | P0  | Shopify                       | HMAC + queue + worker create/cancel              | shopify_service                |
| INT-02 | P1  | Shopify                       | Rate quotes table/path                           | migrations shopify_rate_quotes |
| INT-03 | P1  | Shopify                       | Merchant `/shopify` UI create; admin revoke only | charter IA                     |
| INT-04 | P2  | WooCommerce                   | planned connector contract stub                  | integrations.yaml planned      |
| INT-05 | P1  | NetSuite/Zapier               | `test_netsuite_zapier.py` contracts              | —                              |
| INT-06 | P1  | Merchant outbound webhooks    | delivery + retry                                 | —                              |
| INT-07 | P1  | OAuth third_party             | providers list                                   | oauth                          |
| INT-08 | P1  | Lead ingest bus               | Meta/CAPI/channels                               | lead_ingest                    |
| INT-09 | P2  | Zoho SalesIQ                  | **must not load** (DeferredSite)                 | wave10 whatsapp verify         |
| INT-10 | P1  | Partner developer portal docs | OpenAPI ↔ Postman                                | `validate:developer-portal`    |
| INT-11 | P2  | Integration marketplace flags | phase2/off                                       | marketplace verify             |
| INT-12 | P0  | Matrix file sync              | yaml ↔ INTEGRATIONS.md                           | `validate:integrations-matrix` |

**Missed by request (additions):** SpiceDB, EventBus/DLQ, Mailpit, Staff IdP, Nominatim geocode fallback, Checkr, Stripe Identity, Doppler/`APP_ENV` immutability, OpenAPI census, model-ownership allowlists, Valkey override, partner idempotency, lead CAPI, blog CMS, system-tests UI, privacy DSR, standing orders, verticals (medical/food/construction), investor metrics, NIM propose-only.

---

## 10. UI / UX page matrices

### 10.1 Admin — `UI-A-*` (smoke each route)

For **every** route in §1.4: unauth redirect · auth load shell · primary data fetch · empty state · error banner · tablet (`validate:admin-tablet`).

| ID       | P   | Sub-focus                                             | Expected                           |
| -------- | --- | ----------------------------------------------------- | ---------------------------------- |
| UI-A-OPS | P0  | `/operations` board + Optimize + Copilot + PushHealth | no custom GPS SoT; Fleetbase-first |
| UI-A-ORD | P0  | `/orders` list+detail assist                          | propose→confirm                    |
| UI-A-MER | P0  | `/merchants` list vs detail tabs                      | list=scan; detail=operate          |
| UI-A-DRV | P0  | `/drivers` 360 + verification badges                  | human approve status               |
| UI-A-FIN | P0  | `/finance` + invoice detail                           | AR + COD queue                     |
| UI-A-PRC | P0  | `/pricing` center                                     | FSA/rates                          |
| UI-A-SET | P0  | `/settings` panels + import/restore audit             | project mode not clickable         |
| UI-A-SYS | P1  | `/system-health` `/system-tests`                      | probes honest                      |
| UI-A-CRM | P1  | leads pipeline/calendar                               | ingest settings                    |
| UI-A-NTY | P1  | `/notifications` + account security                   | step-up where required             |
| UI-A-BLG | P2  | blog CRUD                                             | media                              |

### 10.2 Merchant — `UI-M-*`

| ID      | P   | Page                            | Expected                                              |
| ------- | --- | ------------------------------- | ----------------------------------------------------- |
| UI-M-01 | P0  | `/book`                         | quote→book; Places autocomplete                       |
| UI-M-02 | P0  | `/orders` `/orders/[id]`        | track/print/POD mapping                               |
| UI-M-03 | P0  | `/billing`                      | invoices; not alert prefs                             |
| UI-M-04 | P1  | `/settings`                     | profile/locations/tax; **not** API keys mint by admin |
| UI-M-05 | P1  | `/team`                         | seats                                                 |
| UI-M-06 | P1  | `/shopify` `/api`               | merchant creates keys/Shopify                         |
| UI-M-07 | P1  | `/routes` bulk under-nav OK     | intentional EXTRA_ROUTE                               |
| UI-M-08 | P2  | `/reports` `/referrals` `/help` | scoped                                                |
| UI-M-09 | P2  | `/notifications`                | prefs                                                 |

### 10.3 Customer / Driver web / Website

- Customer: full cases in sibling doc (`C-UI-*`).
- Driver web: each §1.7 route + BFF auth cookie path (`UI-D-*` P0 dashboard/jobs/wallet; P1 docs/onboarding; P2 training/emergency).
- Website: CTA quote/book (`UI-W-01` P0); track (`UI-W-02`); no Phase3 SKU claims (`validate:design` / product-vision); SEO/a11y suite P1.

### 10.4 Mobile — `MOB-*`

| ID       | P   | Case                                                     | Expected          |
| -------- | --- | -------------------------------------------------------- | ----------------- |
| MOB-D-01 | P0  | Handshake + SignIn                                       | `:8001`           |
| MOB-D-02 | P0  | Jobs/JobDetail/Route                                     | assigned only     |
| MOB-D-03 | P1  | FCM register                                             | push              |
| MOB-D-04 | P1  | Docs upload                                              | web-first CTAs OK |
| MOB-C-01 | P0  | SignIn + Track only                                      | depth skip        |
| MOB-X-01 | P0  | No Fleetbase HTTP / SocketCluster in `apps/mobile-*/src` | CI                |

### 10.5 UX cross-cuts — `UX-*`

| ID    | P   | Guard                                          |
| ----- | --- | ---------------------------------------------- |
| UX-01 | P1  | `validate:portal-ux`                           |
| UX-02 | P1  | `validate:booking-a11y`                        |
| UX-03 | P1  | `validate:pagination`                          |
| UX-04 | P1  | `validate:design-copy` + no false AI marketing |
| UX-05 | P2  | i18n parity website                            |
| UX-06 | P2  | tracking maps tiles                            |

---

## 11. Database / models — `DB-*`

| ID    | P   | Case                    | Expected              | Guard                    |
| ----- | --- | ----------------------- | --------------------- | ------------------------ |
| DB-01 | P0  | Alembic head single     |                       | `verify_alembic_head`    |
| DB-02 | P0  | Model ownership writes  | only owning engine    | `verify_model_ownership` |
| DB-03 | P0  | Integrity FKs           | migration t2u3…       | integrity waves          |
| DB-04 | P1  | Order cents integer     | no float money        | invoice cents            |
| DB-05 | P1  | Soft-close merchant     | no DELETE             | lifecycle                |
| DB-06 | P1  | Sandbox flag ≠ APP_ENV  | commercial label only | skips                    |
| DB-07 | P2  | Referral credits tables |                       | migration z8…            |
| DB-08 | P2  | CRM collapse migration  |                       | x6…                      |

God nodes to regression-test first (Graphify): **Settings (884)** · **Order (520)** · **MerchantContext (465)** · **AdminContext (339)** · **require_module (205)**.

---

## 12. Docker / infra — `DOC-*`

| ID     | P   | Case                                                                  | Expected             |
| ------ | --- | --------------------------------------------------------------------- | -------------------- |
| DOC-01 | P0  | Compose image pins                                                    | no `:latest`         |
| DOC-02 | P0  | Valhalla digest-pinned scripted image                                 |                      |
| DOC-03 | P0  | OSRM from same GTA PBF                                                |                      |
| DOC-04 | P0  | Mailpit not Mailhog                                                   |                      |
| DOC-05 | P0  | Fleetbase Valkey 8 override                                           |                      |
| DOC-06 | P0  | Ports: API 8001, FB 8000, Valhalla 8002, OSRM 5000, portals 3000–3004 |                      |
| DOC-07 | P1  | Worker + API share DB/Redis                                           |                      |
| DOC-08 | P1  | `verify_db_pool` / managed postgres                                   |                      |
| DOC-09 | P1  | `verify_api_stateless`                                                |                      |
| DOC-10 | P2  | Lockfile freshness                                                    | `validate:lockfiles` |

---

## 13. Worker / EventBus — `WRK-*`

| ID     | P   | Case                                      | Expected                       |
| ------ | --- | ----------------------------------------- | ------------------------------ |
| WRK-01 | P0  | HandlerRegistry dispatch                  |                                |
| WRK-02 | P0  | Redis idempotency store                   | no double handle               |
| WRK-03 | P0  | DLQ on poison                             |                                |
| WRK-04 | P0  | DomainEventType catalog parity            | `test_event_catalog_parity.py` |
| WRK-05 | P1  | Fleetbase retry processor                 |                                |
| WRK-06 | P1  | Shopify queued webhook processor          |                                |
| WRK-07 | P1  | Billing/dispatch/notifications processors | respective tests               |
| WRK-08 | P2  | Optimize run queue                        |                                |

---

## 14. Architecture contracts — `ARCH-*`

| ID      | P   | Guard / case                                                                                                                                                                                                |
| ------- | --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| ARCH-01 | P0  | `pnpm validate:architecture` (spatial math, boundaries, census, vendor leaves, model ownership, api stateless, db pool, FB sync SLO, managed PG, masterrule, integrations matrix, api readme, doc pointers) |
| ARCH-02 | P0  | `pnpm validate:golden-rules`                                                                                                                                                                                |
| ARCH-03 | P0  | `pnpm validate:fleetbase-first`                                                                                                                                                                             |
| ARCH-04 | P0  | `pnpm validate:d2` contracts                                                                                                                                                                                |
| ARCH-05 | P1  | `pnpm validate:router-audit` thin routers                                                                                                                                                                   |
| ARCH-06 | P1  | `pnpm validate:enterprise-security` + identity                                                                                                                                                              |
| ARCH-07 | P1  | `pnpm validate:observability`                                                                                                                                                                               |
| ARCH-08 | P1  | `pnpm validate:p0` / `validate:e2e` local                                                                                                                                                                   |
| ARCH-09 | P2  | `pnpm validate:phase2-flags` default off                                                                                                                                                                    |
| ARCH-10 | P2  | Doc pointer stubs / governance                                                                                                                                                                              |

---

## 15. Suggested execution order (Jeff Dean)

1. **HS-*** handshakes (compose up → green).
2. **ARCH-01** + OpenAPI census.
3. **AUTH-*** + **API-B-*** quote/book/track.
4. **MAP-*** + **FB-*** sync.
5. **PAY-*** + **NOTIF-***.
6. Persona UI smokes **UI-A/M/C/D** critical paths.
7. **INT-Shopify** + partner API.
8. Expand engine unit gaps from god nodes.
9. Website/SEO/UX validators.
10. Mobile handshake + intentional-depth skips documented.

**Coverage heuristic:** treat Graphify god nodes + every OpenAPI tag + every `page.tsx` as a checklist cell (smoke ≥ P2). Deep behavioral cases stay on money/trust/identity loops (P0–P1).

---

## 16. Sensor sessions — status

| Session     | Status                         | Emit already folded above                                                    |
| ----------- | ------------------------------ | ---------------------------------------------------------------------------- |
| A Graphify  | **done**                       | census, HS-01…24, god nodes                                                  |
| B CodeGraph | **done** (Maps/Orchestrator)   | HS-25, MAP-11…13; deeper ORM field cases → `ENG-*` / `DB-*` as you implement |
| C Ripwire   | **done** (handshakes / probes) | HS-26/27; `_probe_vroom` expand; integration_health callers                  |

**Still useful when coding a slice (new session, one sensor):**

```
# CodeGraph — field-level schemas
npx -y @colbymchenry/codegraph explore "Order Quote Payment Merchant Driver" --path .

# Ripwire — before editing a thin router
ripwire . --cache=.ripwire --for="<change in words>"
ripwire . --cache=.ripwire --callers=SYM
ripwire . --cache=.ripwire --impact=SYM
```

---

## 17. How to add a case

1. Pick prefix + priority.
2. Name owning route/engine/file (after sensor).
3. Link seed test or `validate:*` if exists; else mark `NEW`.
4. Never add cases that contradict [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) as “bugs”.
5. After folder-graph change: `graphify update .` (not every line edit).

---

## 18. You asked for — coverage map (nothing orphaned)

| You asked                                   | Where covered                                                                                                           |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Models / database / Alembic                 | §11 `DB-*` · persona DB sections · `test_postgres_smoke.py`                                                             |
| Docker / compose / Valkey / Mailpit         | §12 `DOC-*` · FULL_STACK §2 · SYSTEM `DOC-*`                                                                            |
| Fleetbase connection + handshakes           | SYSTEM §2 · this §6 `FB-*` · HS-11..13                                                                                  |
| PorterChain pages + subpages                | §1 inventory · §10 UI · ADMIN / MERCHANT / CUSTOMER / DRIVER docs                                                       |
| API / FastAPI / endpoints                   | §3 · OpenAPI 568/639 · census guard                                                                                     |
| Microservices / engines                     | §1.2–1.3 · §4 `ENG-*`                                                                                                   |
| Firebase / push                             | §8 `NOTIF-*` · DIAG `firebase` · DRIVER NOTIF-D                                                                         |
| Clerk / Staff IdP / SpiceDB                 | §3.1 `AUTH-*` · SYSTEM §4                                                                                               |
| VROOM / Valhalla / OSRM / Google            | §5 `MAP-*` · ROUTE_OPTIMIZATION · SYSTEM §3                                                                             |
| Email / Mailpit / Zepto                     | §8 · HS-17 · DIAG `mailpit` / `email_smtp`                                                                              |
| Notification system                         | §8 · notification_engine tests                                                                                          |
| Backend / UI / UX                           | §4 · §10 · `validate:portal-ux` / design validators                                                                     |
| Architecture / handshakes                   | §2 HS · §14 ARCH · SYSTEM §1                                                                                            |
| Shopify                                     | §9 INT · MERCHANT matrix · shopify_* tests                                                                              |
| Other ERP (NetSuite / Zapier / partner-api) | §9 · SYSTEM §7 · `test_netsuite_zapier.py`                                                                              |
| Worker / EventBus                           | §13 `WRK-*`                                                                                                             |
| Website / SEO / GTM                         | [WEBSITE_PERSONA_DEV_TEST_CASES.md](WEBSITE_PERSONA_DEV_TEST_CASES.md) · §1.8 · `validate:website-seo`                  |
| Mobile                                      | §1.9 · [MOBILE_DRIVER_DEV_TEST_CASES.md](MOBILE_DRIVER_DEV_TEST_CASES.md) · DRIVER MOB-D summary · CUSTOMER mobile skip |
| Diagnostics Test Center                     | ADMIN §0.3 · SYSTEM DIAG-* · `/system-tests`                                                                            |
| Checkr / Stripe Identity                    | DRIVER verification · intentional skips                                                                                 |
| Lead ingest / Meta CAPI                     | ADMIN leads · `test_lead_*`                                                                                             |
| Project mode / Doppler                      | HS-24 · PCD_INTENTIONAL_SKIPS                                                                                           |

**Also required (easy to miss — already in catalogs):** EventBus, SpiceDB, Staff IdP, FSA/GTA150, sequence-store CAS, Prometheus `/metrics`, integrity/IDOR, blog CMS, websocket live map (PC not SC), COD Connect additive to Checkout.

**Do not invent greenfield product tests for:** WooCommerce/SAP/QuickBooks as first-class, Firebase Auth, Google Distance Matrix, second VROOM client, SocketCluster in web, Zoho SalesIQ, full Ontario tiles, auto-approve drivers — assert **absence** via ARCH / intentional skips.
