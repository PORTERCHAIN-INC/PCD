# PorterChain — full-stack development test cases

**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md) (start there). This file owns **compose→spatial→UI heatmap + load**.

**Status:** living catalog for **local / CI development** (not Doppler prod soak).  
**Mapped:** 2026-09-17 via **Graphify only** (one sensor / session) + `ARCHITECTURE.md` + `integrations.yaml` + OpenAPI census (568 paths / 639 ops) + existing pytest / `pnpm validate:*`.  
**Specialized catalogs (do not duplicate — expand those first):**

| Catalog                                                                        | Scope                                                                |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------- |
| [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)       | Customer web + Admin Customers                                       |
| [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) | Fleetbase adapter modules, Shopify, ERP, Clerk/Stripe/FCM handshakes |
| [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)   | Valhalla / OSRM / VROOM optimize paths                               |
| [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md)               | Driver 360 + verification                                            |
| [ADMIN_SUPERADMIN_DEV_TESTCASES.md](ADMIN_SUPERADMIN_DEV_TESTCASES.md)         | Admin / superadmin surfaces                                          |
| [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)     | Merchant portal + admin merchant                                     |
| [WEBSITE_PERSONA_DEV_TEST_CASES.md](WEBSITE_PERSONA_DEV_TEST_CASES.md)         | Website GTM + quote/book/track + SEO                                 |

**Policy holds:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) — cases marked **SKIP-POLICY** must assert the _hold_, not implement the forbidden path.

### Sensor follow-ups (do not run in the Graphify session)

| Next | Tool                                       | Use when implementing cases                                                           |
| ---- | ------------------------------------------ | ------------------------------------------------------------------------------------- |
| B    | CodeGraph MCP `codegraph_explore`          | Pydantic/ORM for Maps, Order, Quote, Stripe, Clerk, Shopify, FCM payloads             |
| C    | Ripwire `--for` / `--callers` / `--impact` | Thin routers, `FleetbaseClient`, Stripe `sdk.py`, Clerk registry, portal `lib/api.ts` |

### Graphify anchors used

| Query / path                                      | Finding                                                                                                                                                           |
| ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| God nodes                                         | `Settings`, `Order`, `MerchantContext`, `AdminContext`, `Merchant`, `require_module`, `Driver`                                                                    |
| `explain MapsService`                             | Hub for Valhalla/OSRM; callers: pricing `resolve_route_distance`, Control Tower scoring, LiveMap, public tracking, merchant tracking, driver nav                  |
| `path MapsService ↔ FleetbaseClient` (undirected) | 4 hops via scoring / matrix tests — **no direct Valhalla→Fleetbase edge** (correct: VROOM lives in adapter orchestrator)                                          |
| Diagnostics probes                                | `_probe_valhalla`, `_probe_osrm`, `_probe_vroom`, `_probe_fleetbase*`, `_probe_clerk`, `_probe_stripe`, `_probe_firebase`, `_probe_mailpit`, `_probe_google_maps` |

---

## 0. ID scheme, priorities, how to run

| Prefix    | Layer                                                   |
| --------- | ------------------------------------------------------- |
| `DOC-*`   | Docker / compose / health / ports / image pins          |
| `SPA-*`   | Spatial: Valhalla → OSRM → (banned Google routing)      |
| `FB-*`    | Fleetbase adapter + PHP console + VROOM orchestrator    |
| `HS-*`    | Cross-system handshakes (PC ↔ FB ↔ Valhalla ↔ worker)   |
| `API-*`   | FastAPI routers / OpenAPI census personas               |
| `ENG-*`   | `*_engine` unit / service                               |
| `AUTH-*`  | Clerk / Staff IdP / SpiceDB / RBAC / IDOR               |
| `PAY-*`   | Stripe Checkout / COD Connect / webhooks                |
| `NOTIF-*` | FCM / email / Mailpit / EventBus notifications          |
| `INT-*`   | Shopify / ERP / OAuth / merchant-api / inbound webhooks |
| `DB-*`    | Postgres / Alembic / Redis / Valkey / integrity         |
| `A-UI-*`  | Admin portal pages                                      |
| `M-UI-*`  | Merchant portal pages                                   |
| `C-UI-*`  | Customer portal (see customer catalog)                  |
| `D-UI-*`  | Driver web BFF `:3003`                                  |
| `W-UI-*`  | Website `:3000`                                         |
| `MOB-*`   | Expo driver / customer shells                           |
| `ARCH-*`  | Architecture contracts / folder law / vendor leaves     |
| `UX-*`    | A11y / tablet / design / copy / maps UX                 |
| `LOAD-*`  | Load / soak (k6 under `tests/load`)                     |

**Priority:** P0 ship-blocker · P1 trust/money/dispatch · P2 regression · P3 polish/Phase2.

**Each case shape:** Precondition → Steps → Expected → Tags → Existing hook (if any).

### Run map (dev)

| Suite                 | Command / location                                                          |
| --------------------- | --------------------------------------------------------------------------- |
| API unit/integration  | `cd apps/api && PYTHONPATH=src pytest` (~202 top-level + `tests/services/`) |
| Maps costing          | `services/python/tests/test_valhalla_costing.py`                            |
| Fleetbase adapter     | `services/fleetbase-adapter/tests/`                                         |
| Pricing               | `services/pricing-engine/tests/`                                            |
| Architecture gates    | `pnpm validate:architecture`                                                |
| Vendor leaves         | `scripts/verify_vendor_leaves.py` (inside architecture)                     |
| P0 loop               | `pnpm validate:p0:fast` / `pnpm validate:p0`                                |
| E2E validation        | `pnpm validate:e2e`                                                         |
| Portal smoke          | `pnpm validate:portal-smoke`                                                |
| Mobile smoke          | `pnpm validate:mobile-smoke`                                                |
| Integrations matrix   | `pnpm validate:integrations-matrix`                                         |
| Admin System Tests UI | `:3002` → `/system-tests` (probes live against local stack)                 |

---

## 1. Handshake matrix (Valhalla ↔ Fleetbase ↔ PorterChain)

These are the **Jeff Dean** cases: prove the trunk, not every leaf.

| ID    | P   | Precondition                     | Steps                                                       | Expected                                                                                  | Hook                                 |
| ----- | --- | -------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------ |
| HS-01 | P0  | compose `routing` + `core` up    | Admin System Health / `_probe_valhalla(live)`               | status ok; tiles/status JSON; GTA bbox responds                                           | diagnostics                          |
| HS-02 | P0  | Valhalla down, OSRM up           | Quote / `MapsService.route_with_source` Toronto→Mississauga | source=`osrm`; distance>0; no Google                                                      | `test_routing.py`                    |
| HS-03 | P0  | both spatial down                | Quote                                                       | fail-closed error; **no** public OSRM unless `osrm_allow_public_demo` + labeled           | vendor leaves                        |
| HS-04 | P0  | adapter + Fleetbase API healthy  | `_probe_fleetbase_adapter(live)` + `_probe_fleetbase`       | adapter circuit closed; auth OK                                                           | adapter tests                        |
| HS-05 | P0  | VROOM via Fleetbase orchestrator | `_probe_vroom(live)`                                        | probe hits **orchestrator engines**, never PC HTTP VROOM client                           | `diagnostics_fleetbase_probes`       |
| HS-06 | P0  | `VROOM_ROUTER=valhalla`          | Optimize / route-import optimize 5 stops                    | solution returns; fuel scorecard optional; no `*_engine` import of VROOM                  | adapter `test_orchestrator.py`       |
| HS-07 | P0  | book retail or merchant order    | Order → Fleetbase sync (`fleetbase_engine` RetryQueue)      | FB public id stored; retry on 5xx; webhook status maps via `StatusTranslator`             | `test_fleetbase_*`                   |
| HS-08 | P0  | driver online in Fleetbase       | Control Tower suggestions                                   | ranked drivers use **matrix from MapsService**, assignment write goes **through adapter** | scoring + adapter                    |
| HS-09 | P1  | live GPS SoT in Fleetbase        | Public track + merchant track                               | PC reads via facade; portals never call `:8000`                                           | `validate:tracking-maps`             |
| HS-10 | P0  | worker running                   | EventBus smoke + Fleetbase retry drain                      | events land; queue depth drops                                                            | `_probe_event_bus`, `_probe_workers` |
| HS-11 | P0  | OpenAPI snapshot                 | `pnpm docs:openapi` + census                                | 639 ops classified; new untagged path fails CI                                            | `openapi_census.py`                  |
| HS-12 | P1  | mobile driver handshake          | Expo handshake probe to `:8001`                             | `/driver-api/v1` only; no Fleetbase host                                                  | mobile handshake.ts                  |

**Invariant (assert in ARCH-\*):** There is **no** directed Graphify path Valhalla→Fleetbase. Spatial for pricing/ETA = MapsService. Sequencing/TSP = Fleetbase VROOM. GPS SoT = Fleetbase.

---

## 2. Docker / infra (`DOC-*`)

| ID     | P   | Case                                                 | Expected                                                           |
| ------ | --- | ---------------------------------------------------- | ------------------------------------------------------------------ |
| DOC-01 | P0  | `postgres:18` healthy                                | `pg_isready`; Alembic head applies                                 |
| DOC-02 | P0  | `redis:8.8` ping                                     | staff sessions + rate limit + caches work                          |
| DOC-03 | P0  | `spicedb` migrate + serve                            | gRPC health; Check path used (no cache-allows)                     |
| DOC-04 | P0  | `mailpit` up (not Mailhog)                           | SMTP accept; UI messages list                                      |
| DOC-05 | P0  | `valhalla` digest-pinned image                       | container healthy on `:8002`                                       |
| DOC-06 | P0  | `osrm` from same GTA ±150 km PBF                     | `:5000` route OK; README warns graph not committed                 |
| DOC-07 | P0  | `vroom` local                                        | only via Fleetbase orchestrator path                               |
| DOC-08 | P0  | Fleetbase stack + Valkey 8 override                  | no upstream `redis:4` for FB cache                                 |
| DOC-09 | P0  | MySQL 8 for Fleetbase                                | healthcheck passes                                                 |
| DOC-10 | P1  | no `:latest` floating tags in compose                | `validate:architecture` / pin audit                                |
| DOC-11 | P1  | port map                                             | 3000–3004 portals, 8001 API, 8002 Valhalla, 5000 OSRM, 8000 FB API |
| DOC-12 | P1  | `prepare-valhalla-gta.sh` then `prepare-osrm-gta.sh` | extract is GTA±150 not full Ontario                                |
| DOC-13 | P2  | `tune-valhalla-json.py` on 4GB host                  | valhalla.json patched without changing extract                     |
| DOC-14 | P0  | API + worker env from Doppler/local                  | `APP_ENV` boot-time only; project-mode immutable                   |

---

## 3. Spatial stack (`SPA-*`) — Valhalla / OSRM / Google

Canonical client: `services/python/porterchain_services/maps/service.py`.

| ID     | P   | Case                                          | Expected                                                | Seed                         |
| ------ | --- | --------------------------------------------- | ------------------------------------------------------- | ---------------------------- |
| SPA-01 | P0  | `route` GTA in-bounds                         | polyline + meters + seconds                             | MapsService                  |
| SPA-02 | P0  | `route_with_source` reports engine            | `valhalla` when up                                      |                              |
| SPA-03 | P0  | Valhalla fail → OSRM fallback                 | source flips; same contract                             | `test_routing.py`            |
| SPA-04 | P0  | `route_distance_meters` for pricing           | used by `resolve_route_distance`                        | pricing                      |
| SPA-05 | P0  | `matrix_durations` N×N                        | Control Tower scoring uses matrix not haversine for ops | `test_assignment_scoring.py` |
| SPA-06 | P1  | `isochrone`                                   | diagnostics / coverage tools                            |                              |
| SPA-07 | P1  | `eta_between`                                 | merchant tracking ETA cache                             | tracking_views               |
| SPA-08 | P1  | `optimized_route` / sequence                  | maps.sequence only; no ops haversine                    | `verify_no_ops_spatial_math` |
| SPA-09 | P0  | costing: box → `truck`, van/car → `auto`      | `test_valhalla_costing.py`                              |                              |
| SPA-10 | P0  | engines never call `_valhalla_*` / `_osrm_*`  | public API only                                         | ARCH                         |
| SPA-11 | P0  | Google Places autocomplete                    | UX only; never distance                                 | packages/maps                |
| SPA-12 | P0  | Google tiles on track map                     | render OK                                               | `validate:tracking-maps`     |
| SPA-13 | P0  | Google Distance Matrix / Directions for price | **must fail CI** / banned                               | vendor leaves                |
| SPA-14 | P0  | public `router.project-osrm.org` default      | **forbidden** unless labeled last-resort flag           |                              |
| SPA-15 | P1  | out-of-GTA quote                              | service-area reject (Ontario/GTA policy)                | `test_service_area.py`       |
| SPA-16 | P1  | fuel scorecard enrichment on optimize         | optional metrics; does not own TSP                      | fuel_scorecard               |
| SPA-17 | P2  | polyline decode/encode                        | `test_polyline.py`                                      |                              |

---

## 4. Fleetbase + VROOM (`FB-*`)

| ID    | P   | Case                                           | Expected                                          | Seed                                                     |
| ----- | --- | ---------------------------------------------- | ------------------------------------------------- | -------------------------------------------------------- |
| FB-01 | P0  | `FleetbaseClient` timeout + breaker            | opens on errors; recovers                         | `test_client_timeout_breaker.py`                         |
| FB-02 | P0  | adapter contract parity with PC                | mappers round-trip                                | `test_contract.py`, `test_fleetbase_adapter_contract.py` |
| FB-03 | P0  | manifests / stop payload                       | booking sync shape                                | `test_manifests.py`                                      |
| FB-04 | P0  | orchestrator optimize                          | VROOM behind adapter                              | `test_orchestrator.py`                                   |
| FB-05 | P1  | tracking playback                              | positions from REST poll not SocketCluster in web | `test_tracking_playback.py`                              |
| FB-06 | P0  | webhook signature + process                    | status → PC `OrderState`                          | webhook_processor                                        |
| FB-07 | P0  | webhook retry / DLQ                            | RetryQueue drains                                 | `test_fleetbase_webhook_retry.py`                        |
| FB-08 | P0  | public ids format                              | `test_fleetbase_public_ids.py`                    |                                                          |
| FB-09 | P0  | sync health SLO                                | `verify_fleetbase_sync_slo.py`                    |                                                          |
| FB-10 | P0  | portals never fetch FB HTTP / SC               | CI scan `apps/*/src`                              | vendor leaves                                            |
| FB-11 | P0  | mobile never embeds `:8000` / `fleetbase` HTTP | CI                                                | ARCH mobile Required                                     |
| FB-12 | P1  | POD download / scan gate                       | driver jobs via PC API                            | `test_d3_dispatch_pod_contract.py`                       |
| FB-13 | P1  | GPS ingest waves                               | last-known via engine; SoT FB                     | `test_gps_ingest_wave*.py`                               |
| FB-14 | P1  | status translator edge cases                   | unknown FB status fail-safe                       | `test_status_translator.py`                              |
| FB-15 | P2  | admin does not link to the Ember console       | bond is API only, no embedded SC                  | system-links                                             |
| FB-16 | P0  | no PorterChain VROOM client under `*_engine`   | import guard                                      | ARCH Required                                            |

---

## 5. FastAPI / personas / engines (`API-*`, `ENG-*`)

### 5.1 Persona prefixes (census)

| Persona      | Prefix                                          | Auth                       | Suite focus                             |
| ------------ | ----------------------------------------------- | -------------------------- | --------------------------------------- |
| Staff        | `/v1/admin`                                     | Staff IdP / `staff_sess_*` | ops, finance, CT, settings, diagnostics |
| Merchant     | `/v1/merchant`                                  | Clerk org                  | book, orders, billing, Shopify          |
| Partner      | `/v1/merchant-api`                              | API key + idempotency      | PARTNER_GUIDE                           |
| Driver       | `/driver-api/v1`                                | Clerk Bearer               | jobs, POD, wallet                       |
| Retail       | `/v1/quotes` `/v1/bookings`                     | session / checkout         | website + customer                      |
| Public track | `/v1/orders/{tracking_number}`                  | none                       | track pages                             |
| Webhooks     | `/webhooks/clerk\|stripe\|fleetbase\|checkr\|…` | signatures                 | money + identity + execution            |

| ID     | P   | Case                             | Expected                            |
| ------ | --- | -------------------------------- | ----------------------------------- |
| API-01 | P0  | unauthenticated admin            | 401                                 |
| API-02 | P0  | wrong persona token on admin     | 403                                 |
| API-03 | P0  | `require_module` matrix          | module-gated routes deny            | leads/drivers modules              |
| API-04 | P0  | IDOR merchant order              | cannot read other org               | `test_idor.py`                     |
| API-05 | P0  | merchant-api idempotency replay  | same key → same body                | `test_merchant_api_idempotency.py` |
| API-06 | P0  | wholesale route templates stay   | `/v1/admin/route-templates` present | `test_removed_ops_endpoints.py`    |
| API-07 | P0  | error envelope shape             | stable `code`/`message`             | `test_error_envelope.py`           |
| API-08 | P0  | rate limit fixed window          | 429 after limit                     | `test_gateway_rate_limit.py`       |
| API-09 | P1  | readiness / health               | db+redis+deps                       | `test_health.py`                   |
| API-10 | P0  | OpenAPI census freeze            | new path must be tagged             |                                    |
| API-11 | P1  | dual merchant book paths         | both stay; documented               | census note                        |
| API-12 | P1  | webhook CRUD vs integration logs | different callers kept              |                                    |

### 5.2 Engine ownership (sample P0/P1)

| ID          | Engine                                     | Cases                                                                      |
| ----------- | ------------------------------------------ | -------------------------------------------------------------------------- |
| ENG-BOOK-*  | `booking_engine`                           | quote → book → pay → track snapshot; draft transitions                     |
| ENG-MER-*   | `merchant_engine`                          | onboarding, book, bulk, route import, Shopify, privacy DSR                 |
| ENG-ADM-*   | `admin_engine`                             | Control Tower, LiveMap, finance board, merchant360, driver360, diagnostics |
| ENG-PRICE-* | `pricing_engine` + services/pricing-engine | FSA GTA150, liftgate, rate card, merchant policy                           |
| ENG-BILL-*  | `billing_engine`                           | ledger, invoices, COD policy (not Stripe SDK)                              |
| ENG-FB-*    | `fleetbase_engine`                         | sync, webhook, tracking facade, nav geometry cache                         |
| ENG-DRV-*   | `driver_engine`                            | façade over FB; wallet ledger; verification                                |
| ENG-NOTIF-* | `notification_engine`                      | FCM + email orchestration                                                  |
| ENG-AUTHZ-* | `authz`                                    | SpiceDB Check; TupleWriter                                                 |
| ENG-INT-*   | `intelligence_engine`                      | phase2 flags off by default                                                |
| ENG-SUP-*   | `support_engine`                           | claims/tickets ownership                                                   |
| ENG-CRM-*   | collaboration / CRM                        | leads, nurture, merge (phase2 gated where required)                        |

Seed files already dense under `apps/api/tests/test_*.py` and `tests/services/` — expand gaps; do not fork parallel trees.

---

## 6. Auth / identity (`AUTH-*`)

| ID      | P   | Case                                                           | Expected                                        |
| ------- | --- | -------------------------------------------------------------- | ----------------------------------------------- |
| AUTH-01 | P0  | Clerk triad per portal via `env/clerk.env` + `pnpm clerk:sync` | no `ADMIN_CLERK_SECRET_KEY` names               |
| AUTH-02 | P0  | local `CLERK_DEV_BYPASS` + portal bypass                       | Bearer `dev` works **only** when APP_ENV allows |
| AUTH-03 | P0  | customer Clerk bypass as product shortcut                      | **forbidden**                                   |
| AUTH-04 | P0  | staff IdP passkey/magic + Redis session                        | cookie → Bearer path                            |
| AUTH-05 | P0  | Firebase Auth for login                                        | **forbidden** (FCM only)                        |
| AUTH-06 | P0  | SpiceDB Check no caching allows                                | `test_spicedb_authz.py`                         |
| AUTH-07 | P0  | hybrid RBAC modules                                            | `test_hybrid_rbac.py`                           |
| AUTH-08 | P1  | Clerk webhooks user sync                                       | registry binds                                  | `test_clerk_registry.py`      |
| AUTH-09 | P1  | OAuth token merchant resolve                                   | thin router                                     | oauth                         |
| AUTH-10 | P1  | enterprise SSO / identity                                      | phase flags                                     | `test_enterprise_identity.py` |
| AUTH-11 | P0  | project mode flip via UI                                       | **403 immutable**                               | intentional skip              |
| AUTH-12 | P1  | driver vs driver-web auth paths differ                         | BFF cookie vs mobile Bearer — both valid        |

---

## 7. Money (`PAY-*`)

| ID     | P   | Case                                                     | Expected                                  |
| ------ | --- | -------------------------------------------------------- | ----------------------------------------- |
| PAY-01 | P0  | Stripe Checkout retail prepaid                           | session + webhook → paid booking          |
| PAY-02 | P0  | webhook signature + idempotency table                    | `verify_stripe_webhook_idempotency_table` |
| PAY-03 | P0  | only `porterchain_services/stripe/sdk.py` imports stripe | allowlist                                 |
| PAY-04 | P1  | COD Connect + Payment Link/QR                            | additive; does not break Checkout         |
| PAY-05 | P1  | invoice PDF/CSV cents                                    | `test_invoice_pdf_csv_cents.py`           |
| PAY-06 | P1  | remind / pay link                                        | `test_invoice_remind_pay_link.py`         |
| PAY-07 | P1  | merchant AR / statements                                 | finance + merchant billing                |
| PAY-08 | P1  | driver wallet ledger ownership                           | `driver_engine/wallet_ledger`             |
| PAY-09 | P2  | Stripe mock vs live                                      | `validate:p0:stripe` prod only when asked |

---

## 8. Notifications / email / push (`NOTIF-*`)

| ID       | P   | Case                                    | Expected                          |
| -------- | --- | --------------------------------------- | --------------------------------- |
| NOTIF-01 | P0  | Mailpit receives transactional email    | `_probe_mailpit` / `_probe_email` |
| NOTIF-02 | P0  | FCM config present (dev may be partial) | `_probe_firebase`                 |
| NOTIF-03 | P1  | device token register driver/customer   | notification_engine DeviceService |
| NOTIF-04 | P1  | order status → push + inbox             | admin notifications page lists    |
| NOTIF-05 | P1  | admin web push (Firebase messaging SW)  | token + permission UX             |
| NOTIF-06 | P0  | no second mail/FCM engine               | ARCH                              |
| NOTIF-07 | P1  | EventBus notification fan-out           | smoke_test probe                  |
| NOTIF-08 | P2  | AI usage / notif sandbox tables         | diagnostics AI usage view         |

---

## 9. Integrations beyond core (`INT-*`)

From `integrations.yaml` + engines:

| ID           | P   | Integration                               | Cases                                                                               |
| ------------ | --- | ----------------------------------------- | ----------------------------------------------------------------------------------- |
| INT-SH-01    | P1  | Shopify                                   | OAuth complete; rate quote; book from payload; HMAC webhook; merchant `/shopify` UI |
| INT-SH-02    | P2  | Shopify native app                        | **planned** — assert deferred, do not invent full app                               |
| INT-WC-01    | P2  | WooCommerce                               | planned connector; CSV path if present                                              |
| INT-ERP-01   | P2  | generic ERP                               | merchant-api key + idempotent create order + webhook outbound                       |
| INT-OAUTH-01 | P1  | oauth_third_party                         | client list; token; revoke                                                          |
| INT-KEY-01   | P0  | merchant API keys                         | merchant creates; admin revoke/disable only                                         |
| INT-WH-01    | P1  | merchant outbound webhooks                | delivery + retry + signature                                                        |
| INT-LEAD-01  | P1  | lead ingest bus / CAPI / channel webhooks | `test_lead_*`                                                                       |
| INT-ZOHO-01  | P3  | Zoho SalesIQ                              | website widget optional load                                                        |
| INT-CHK-01   | P1  | Checkr / Stripe Identity webhooks         | driver verification; live keys intentional skip until dashboard ready               |
| INT-MAP-01   | P0  | integrations matrix YAML ↔ docs           | `validate:integrations-matrix`                                                      |

---

## 10. Database / models / Redis (`DB-*`)

| ID    | P   | Case                                         | Expected                    |
| ----- | --- | -------------------------------------------- | --------------------------- |
| DB-01 | P0  | Alembic upgrade head                         | `test_postgres_smoke.py`    |
| DB-02 | P0  | model ownership writers                      | `verify_model_ownership.py` |
| DB-03 | P0  | integrity FKs waves                          | `test_integrity_waves.py`   |
| DB-04 | P1  | CRM JSON queries                             | postgres smoke              |
| DB-05 | P0  | Redis ping + staff session TTL               |                             |
| DB-06 | P1  | Fleetbase Valkey separate from PC Redis      | no cross-contamination      |
| DB-07 | P1  | nav geometry cache TTL                       | fleetbase_engine cache      |
| DB-08 | P2  | referral credits / wallet package migrations | alembic present             |
| DB-09 | P0  | no restored `models.py`                      | import `booking_models`     |

---

## 11. Architecture contracts (`ARCH-*`)

| ID      | P   | Case                                                 | Hook                                 |
| ------- | --- | ---------------------------------------------------- | ------------------------------------ |
| ARCH-01 | P0  | no ops spatial math in admin_engine                  | `verify_no_ops_spatial_math.py`      |
| ARCH-02 | P0  | architecture boundaries                              | `verify_architecture_boundaries.py`  |
| ARCH-03 | P0  | vendor leaves (OSRM URL, VROOM, mobile FB)           | `verify_vendor_leaves.py`            |
| ARCH-04 | P0  | D2 cross-engine freeze                               | `pnpm validate:d2`                   |
| ARCH-05 | P0  | thin routers (no inline db.query)                    | Waves 14–21 done — regression        |
| ARCH-06 | P0  | engine service LOC caps                              | Waves 35–46                          |
| ARCH-07 | P0  | no `core/` `backend/` `personas/` overlays           | folder law                           |
| ARCH-08 | P0  | Google never for distance/ETA/matrix                 |                                      |
| ARCH-09 | P0  | no SocketCluster SDK in web                          |                                      |
| ARCH-10 | P1  | phase2 flags default off                             | `validate:phase2-flags`              |
| ARCH-11 | P1  | AI tools never Valhalla/Fleetbase write / Stripe pay | `validate:ai-governance`             |
| ARCH-12 | P1  | graphify freshness vs HEAD                           | rebuild if stale after folder change |

---

## 12. Admin UI — every page (`A-UI-*`)

Smoke each route: auth gate → load <3s local → primary API 2xx → empty/error states.

| Route                                          | P0 smoke                                                           | Deep cases                                                |
| ---------------------------------------------- | ------------------------------------------------------------------ | --------------------------------------------------------- |
| `/sign-in`                                     | Staff IdP / bypass                                                 | fail closed when prod                                     |
| `/activate-staff`                              | enrollment                                                         |                                                           |
| `/dashboard`                                   | KPIs render                                                        | trends contract `{labels,orders,revenue_cents}`           |
| `/operations`                                  | CT board + OptimizePanel                                           | no custom dispatch rebuild; copilot propose-only          |
| `/orders` · `/orders/[id]`                     | list+360                                                           | assist proposals; invoice actions                         |
| `/merchants` · `/merchants/[id]`               | list+360 tabs                                                      | Overview/Billing/Settings/Pricing ownership per ARCH leaf |
| `/drivers` · `/drivers/[id]`                   | list+360                                                           | verification badges; push/SMS actions                     |
| `/customers` · `/customers/[id]`               | → customer catalog                                                 |                                                           |
| `/finance` · `/finance/invoices/[id]`          | AR + invoice                                                       | pay/remind; COD queue                                     |
| `/pricing`                                     | FSA / rate center                                                  | GTA150                                                    |
| `/leads` · `/pipeline` · `/calendar` · `/[id]` | CRM                                                                | phase2 flags                                              |
| `/booking-drafts` · `/[id]`                    | abandonment                                                        |                                                           |
| `/claims` · `/[id]`                            | support_engine                                                     |                                                           |
| `/support` · `/[id]`                           | tickets                                                            |                                                           |
| `/notifications`                               | inbox                                                              | realtime hook                                             |
| `/inbox`                                       | collab                                                             |                                                           |
| `/blog` · `/new` · `/[id]`                     | CMS                                                                |                                                           |
| `/settings`                                    | panels: coverage, env-owned, integrations, lead ingest, users, FSA | import/restore modals; **no** project-mode toggle         |
| `/system` · `/system-health` · `/system-tests` | probes                                                             | Valhalla/OSRM/FB/VROOM/Clerk/Stripe/FCM/Mailpit           |
| `/account/security`                            | step-up                                                            |                                                           |
| `/admin/system-*`                              | alias routes                                                       | same as ops                                               |

**UX cases:** `validate:admin-tablet`, `validate:portal-ux`, pagination (`validate:pagination`).

---

## 13. Merchant UI (`M-UI-*`)

| Route                            | P0                         | Notes                                                         |
| -------------------------------- | -------------------------- | ------------------------------------------------------------- |
| `/sign-in` `/sign-up`            | Clerk                      |                                                               |
| `/onboarding`                    | activation policy          |                                                               |
| `/dashboard`                     | counts                     |                                                               |
| `/book`                          | quote via MapsService      | Places only for address                                       |
| `/bulk`                          | CSV/template               | idempotency                                                   |
| `/orders` · `/orders/[order_id]` | cancel/duplicate           | tracking sanitize                                             |
| `/track`                         | live                       |                                                               |
| `/routes` · `/routes/[job_id]`   | import optimize → FB VROOM |                                                               |
| `/billing` · invoices            | money                      | not alert prefs                                               |
| `/settings`                      | org config                 | **no** API key mint in admin; merchant creates keys on `/api` |
| `/api`                           | keys + docs                |                                                               |
| `/shopify`                       | OAuth + quotes             |                                                               |
| `/team`                          | seats                      |                                                               |
| `/reports`                       | own metrics                | no fleet internals                                            |
| `/notifications`                 | prefs                      |                                                               |
| `/referrals`                     | credits                    |                                                               |
| `/help`                          |                            |                                                               |

---

## 14. Customer UI (`C-UI-*`)

**SSOT:** [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md).  
Routes: `/`, auth, onboarding, dashboard, book(+success), track(+id), account, notifications.

---

## 15. Driver web (`D-UI-*`) — BFF `:3003`

| Route                                              | P0                                      |
| -------------------------------------------------- | --------------------------------------- |
| `/login`                                           | Clerk                                   |
| `/dashboard`                                       | shift summary                           |
| `/jobs` · `/jobs/[orderId]`                        | accept/POD via BFF → `/driver-api/v1`   |
| `/stops` `/navigation`                             | MapsService geometry; Google tiles only |
| `/shift`                                           | online via FB façade                    |
| `/earnings` `/wallet`                              | ledger                                  |
| `/documents` `/onboarding`                         | verification CTAs (web)                 |
| `/vehicle` `/insurance` `/profile`                 |                                         |
| `/communications` `/inbox`                         |                                         |
| `/support` `/training` `/performance` `/emergency` |                                         |

**ARCH:** do not unify with mobile Bearer path.

---

## 16. Website (`W-UI-*`)

~77 `page.tsx` under `website/src/app/[locale]/…` (marketing, SEO, quote CTA).

| Suite                       | Command                     |
| --------------------------- | --------------------------- |
| SEO/sitemap/robots/schema   | `validate:website-seo`      |
| Product vision / ICP 15s    | `validate:product-vision`   |
| Design / false-AI marketing | `validate:design`           |
| Developer portal            | `validate:developer-portal` |
| Booking a11y                | `validate:booking-a11y`     |
| Quote/book hits `:8001`     | portal smoke + Places       |

P0: home CTA = get quote / request capacity; Phase 3 metrics not sold as today.

---

## 17. Mobile (`MOB-*`)

### Driver Expo

Screens: SignIn, Onboarding, Jobs, JobDetail, Route, Money, Docs, Inbox, Support, More, Invite, ForceUpdate.

| ID       | P   | Case                                           |
| -------- | --- | ---------------------------------------------- |
| MOB-D-01 | P0  | handshake → `:8001` `/driver-api/v1`           |
| MOB-D-02 | P0  | no FB HTTP / SC                                |
| MOB-D-03 | P1  | FCM token register                             |
| MOB-D-04 | P1  | location permission → PC ingest (SoT still FB) |
| MOB-D-05 | P2  | Identity/Checkr CTAs                           | **SKIP-POLICY** web-only for now |

### Customer Expo

SignIn + Track shells only (depth intentional skip).

| ID       | P   | Case                                    |
| -------- | --- | --------------------------------------- |
| MOB-C-01 | P0  | public track by number                  |
| MOB-C-02 | P1  | Clerk session                           |
| MOB-C-03 | P0  | `validate:mobile-smoke` / design parity |

---

## 18. UI/UX cross-cutting (`UX-*`)

| ID    | Hook                                               |
| ----- | -------------------------------------------------- |
| UX-01 | `validate:portal-ux`                               |
| UX-02 | `validate:portal-smoke`                            |
| UX-03 | `validate:tracking-maps`                           |
| UX-04 | `validate:booking-a11y`                            |
| UX-05 | `validate:design-copy` + enterprise visuals + i18n |
| UX-06 | `validate:admin-tablet`                            |
| UX-07 | Empty/loading/error skeletons on every list page   |
| UX-08 | No false “AI insights” product copy                |

---

## 19. Load / soak (`LOAD-*`)

| ID      | File                     | Focus                          |
| ------- | ------------------------ | ------------------------------ |
| LOAD-01 | `tests/load/booking.js`  | quote/book RPS                 |
| LOAD-02 | `tests/load/webhooks.js` | stripe/fleetbase webhook burst |
| LOAD-03 | P2                       | Valhalla matrix under CT load  | latency SLO local |

---

## 20. Coverage heatmap (existing vs gap)

| Area        | Existing strength             | Primary gaps to author next                                   |
| ----------- | ----------------------------- | ------------------------------------------------------------- |
| API pytest  | ~200+ files                   | Live Valhalla/OSRM integration marks (`@pytest.mark.spatial`) |
| Adapter     | contract/orchestrator/breaker | Multi-stop VROOM golden fixtures                              |
| Pricing     | FSA/GTA/liftgate              | End-to-end quote with live MapsService                        |
| Maps python | costing + polyline            | Full MapsService route/matrix against docker                  |
| Portal UI   | validate scripts              | Playwright per-route smoke (admin/merchant/driver)            |
| Mobile      | smoke scripts                 | Detox/Maestro job accept→POD                                  |
| Shopify     | phase4 tests                  | Live shop HMAC fixtures                                       |
| FCM         | partial                       | Emulator push receipt assertions                              |
| E2E         | `validate:e2e`                | Nightly already in `nightly-e2e.yml` — keep green             |

---

## 21. Suggested implementation order (dev layer first)

1. **P0 handshakes HS-01…HS-12** + spatial SPA-01…14 + FB-01…16 — proves Valhalla↔PC↔Fleetbase.
2. **ARCH + DOC** gates in CI (already mostly present — add failing tests only where green is false).
3. **Money + auth** PAY/AUTH P0.
4. **Persona UI smokes** A/M/D/C/W via `validate:portal-smoke` then Playwright.
5. **Integrations** Shopify + merchant-api + webhooks.
6. **NOTIF** Mailpit + FCM register.
7. **P2/P3** Woo/ERP marketplace, mobile depth, load.

When implementing a slice: **new session → CodeGraph** for schemas → **new session → Ripwire** for callers/impact on thin routers/adapters → then write pytest under the owning package.

---

## 22. Traceability

| Source                                    | Role                       |
| ----------------------------------------- | -------------------------- |
| `ARCHITECTURE.md`                         | trunk / folder law / ports |
| `graphify-out/GRAPH_REPORT.md`            | communities / hubs         |
| `docs/api/openapi.json`                   | 568 paths / 639 ops        |
| `integrations.yaml`                       | vendor registry            |
| `docs/PCD_INTENTIONAL_SKIPS.md`           | SKIP-POLICY cases          |
| `docs/CUSTOMER_PERSONA_DEV_TEST_CASES.md` | customer deep catalog      |
| Admin `/system-tests`                     | interactive probe runner   |

---

_Do not treat this file as a license to rebuild Fleetbase, add a PorterChain VROOM client, or use Google for routing. Charter + Fleetbase-first still win._
