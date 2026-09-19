# PorterChain — development test cases catalog (system-wide)

**Entry index:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md) (start there). This file owns **VROOM spine depth** + the missed-surfaces table.

**Status:** living catalog for local/CI development (not prod Doppler validation).  
**Mapped:** 2026-09-17 via Graphify (`query` / `explain` / `god-nodes`) + `ARCHITECTURE.md` + portal page inventory + `INTEGRATIONS.md`.  
**Sensor note:** This session used **Graphify only** (one sensor / session). Do not run CodeGraph or Ripwire in the same session.

| Next moment | Tool                                       | Use for                                                                                                          |
| ----------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------- |
| B           | CodeGraph MCP `codegraph_explore`          | Pydantic/ORM for `Order`, optimize run payloads, Valhalla costing, VROOM normalize shapes, MapsService contracts |
| C           | Ripwire `--for` / `--callers` / `--impact` | Thin routers `operations.py`, `route_imports.py`, Fleetbase/Clerk/Stripe adapters, portal `lib/operations.ts`    |

**Sibling catalogs:** [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md) · [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md) · [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md) · [WEBSITE_PERSONA_DEV_TEST_CASES.md](WEBSITE_PERSONA_DEV_TEST_CASES.md) · entry [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Do-not-test-as-bugs:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) — e.g. no PC VROOM client, no Google Distance Matrix, no SocketCluster in web, no auto-approve drivers from Checkr.

**Charter gate:** Prefer cases that protect capacity utilization, money, identity, trust, and Fleetbase-first boundaries. Reject cases that rebuild vendor boxes inside `*_engine`.

---

## 0. ID scheme & layers

| Prefix    | Layer                                                       |
| --------- | ----------------------------------------------------------- |
| `VR-*`    | VROOM spine (Fleetbase orchestrator + sidecar)              |
| `FB-*`    | Fleetbase adapter / sync / webhooks / POD / GPS SoT         |
| `MAP-*`   | MapsService · Valhalla · OSRM · Google Places/tiles only    |
| `API-*`   | FastAPI `:8001` endpoints / OpenAPI census                  |
| `ENG-*`   | `*_engine` service unit / ownership                         |
| `WK-*`    | Worker / EventBus / retry queue / dispatch processor        |
| `A-UI-*`  | Admin portal `:3002` pages + Control Tower                  |
| `M-UI-*`  | Merchant portal `:3001`                                     |
| `C-UI-*`  | Customer portal `:3004` (detail → sibling catalog)          |
| `D-UI-*`  | Driver web BFF `:3003`                                      |
| `W-UI-*`  | Website `:3000`                                             |
| `MOB-*`   | Expo driver / customer shells                               |
| `AUTH-*`  | Clerk · staff IdP · SpiceDB · RBAC / IDOR                   |
| `PAY-*`   | Stripe Checkout / COD Connect / webhooks / invoices         |
| `NOTIF-*` | FCM · email (Mailpit/Zepto) · inbox · push health           |
| `SHOP-*`  | Shopify OAuth / carrier rates / ingest                      |
| `INT-*`   | Partner API · OAuth · merchant webhooks · ERP-shaped ingest |
| `CRM-*`   | Leads · pipeline · support · claims                         |
| `DB-*`    | Postgres models · Alembic · integrity FKs                   |
| `DOC-*`   | Docker compose · pins · health · profiles                   |
| `ARCH-*`  | Architecture contracts / verify scripts / folder law        |

**Priority:** P0 = ship-blocker · P1 = trust/money/capacity · P2 = polish/regression · P3 = Phase 2+ / intentional depth later.

Each case: **Precondition → Steps → Expected → Layer tags**. Existing pytest seeds are listed under each section — expand; do not duplicate blindly.

---

## 1. Canonical handshake map (Graphify SSOT)

```
Admin OptimizePanel / Merchant route import / Driver reoptimize
        │  :8001
   OrchestratorOpsService / MerchantRouteImportService / driver-platform JobsService
        │
   porterchain_fleetbase_adapter.orchestrator  (RUN_PATH / COMMIT_PATH)
        │  Fleetbase :8000
   Fleetbase FleetOps orchestrator  (engine=vroom)
        │  VROOM_ROUTER=valhalla
   vroom-express sidecar :8030  →  VROOM container  →  Valhalla :8002
                                                    ↘ OSRM :5000 (Maps fallback only; not VROOM matrix)

PorterChain NEVER imports a second VROOM client under *_engine.
Diagnostics probe: diagnostics_fleetbase_probes._probe_vroom → orchestrator engines, not a PC HTTP port.
```

**Spatial split (must stay true in every MAP/VR case):**

| Need                                                 | Engine                            | Forbidden                    |
| ---------------------------------------------------- | --------------------------------- | ---------------------------- |
| Price / quote distance, ETA legs, matrix for scoring | Valhalla → OSRM via `MapsService` | Google Distance Matrix / ETA |
| Multi-stop TSP / allocate / commit manifests         | VROOM via Fleetbase orchestrator  | PC-native VROOM HTTP client  |
| Address UX / map tiles                               | Google Places + JS tiles          | Google for pricing geometry  |

**God nodes (connectivity hubs — regression magnets):** `Settings`, `Order`, `MerchantContext`, `AdminContext`, `Merchant`, `require_module`, `Driver`, `OrderState`.

---

## 2. Surface inventory (every page / subpage)

### 2.1 Admin (`apps/admin` :3002)

| Route                                                              | Sub-surfaces / files                                                                                                                                                                                                                                                  |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `/` → ops shell                                                    | redirects into dashboard                                                                                                                                                                                                                                              |
| `/sign-in/[[...sign-in]]`                                          | Staff IdP (not customer Clerk bypass as product)                                                                                                                                                                                                                      |
| `/activate-staff`                                                  | Staff activation                                                                                                                                                                                                                                                      |
| `/dashboard`                                                       | KPIs, alerts                                                                                                                                                                                                                                                          |
| `/operations`                                                      | Tabs: Board · Exceptions · SLA · Activity; `OptimizePanel`, `DispatchBoard`, `DispatchQueuePanel`, `LiveMapPanel`, `OrdersTablePanel`, `UtilizationPanel`, `ScheduledBatchesPanel`, `DispatcherCopilotPanel`, `PushHealthStrip`, `OpsCommandPalette`, `OpsAlertToast` |
| `/orders`, `/orders/[id]`                                          | List + 360; `Order360Drawer`, `OrderBuilderModal`, `AssignDriverModal`, `OrderAssistPanel`, `ExceptionReasonModal`                                                                                                                                                    |
| `/merchants`, `/merchants/[id]`                                    | List + 360 tabs (overview/billing/pricing/settings/…); GTA matrix, standing orders, billing contacts                                                                                                                                                                  |
| `/drivers`, `/drivers/[id]`                                        | List + 360; docs / verification / presence                                                                                                                                                                                                                            |
| `/customers`, `/customers/[id]`                                    | See sibling catalog                                                                                                                                                                                                                                                   |
| `/leads`, `/leads/[id]`, `/leads/pipeline`, `/leads/calendar`      | CRM pipeline                                                                                                                                                                                                                                                          |
| `/booking-drafts`, `/booking-drafts/[id]`                          | Abandoned / draft recovery                                                                                                                                                                                                                                            |
| `/finance`, `/finance/invoices/[id]`                               | AR, collections, invoice detail                                                                                                                                                                                                                                       |
| `/pricing`                                                         | Pricing center                                                                                                                                                                                                                                                        |
| `/claims`, `/claims/[id]`                                          | Claims                                                                                                                                                                                                                                                                |
| `/support`, `/support/[id]`                                        | Tickets                                                                                                                                                                                                                                                               |
| `/inbox`, `/notifications`                                         | Staff inbox / notification ops                                                                                                                                                                                                                                        |
| `/blog`, `/blog/new`, `/blog/[id]`                                 | Content                                                                                                                                                                                                                                                               |
| `/settings`                                                        | `SettingsCenter` panels: dashboard, coverage, env-owned, integrations, lead ingest, users/directory, FSA rates, import/restore                                                                                                                                        |
| `/account/security`                                                | Staff security / step-up                                                                                                                                                                                                                                              |
| `/system`, `/system-health`, `/system-tests` (+ `/admin/system-*`) | Diagnostics, probes (incl. VROOM), e2e validation                                                                                                                                                                                                                     |

Cross-cutting: `AdminAccessGate`, `AdminAuthProvider`, `lib/api.ts`, `middleware.ts`, BFF `app/api/porterchain/[...path]`, `app/api/auth/ws-token`, Firebase messaging SW, `useAdminNotificationRealtime`.

### 2.2 Merchant (`apps/merchant-portal` :3001)

| Route                                                                     | Notes                                                        |
| ------------------------------------------------------------------------- | ------------------------------------------------------------ |
| `/`, `/sign-in`, `/sign-up`, `/onboarding`                                | Org Clerk                                                    |
| `/dashboard`                                                              | Counts / first-run                                           |
| `/book`                                                                   | Commercial book                                              |
| `/orders`, `/orders/[order_id]`                                           | Board + detail                                               |
| `/routes`, `/routes/[job_id]`                                             | CSV/route import → optimize enqueue                          |
| `/bulk`                                                                   | Bulk jobs                                                    |
| `/track`                                                                  | Merchant tracking views                                      |
| `/billing`, `/billing/invoices/[invoice_id]`                              | Money                                                        |
| `/shopify`                                                                | Connect + carrier                                            |
| `/api`                                                                    | Partner keys / OAuth clients (merchant mints; admin revokes) |
| `/team`, `/settings`, `/notifications`, `/reports`, `/referrals`, `/help` | Org config / ops                                             |

### 2.3 Customer (`apps/customer` :3004)

Welcome · auth · onboarding · dashboard · book · book/success · track · track/[n] · account · notifications — **full cases in sibling catalog**.

### 2.4 Driver web (`apps/driver-portal` :3003)

| Route                                                                                             | Notes                                        |
| ------------------------------------------------------------------------------------------------- | -------------------------------------------- |
| `/`, `/login`                                                                                     | Clerk → BFF `/api/driver` → `/driver-api/v1` |
| `/dashboard`, `/jobs`, `/jobs/[orderId]`, `/stops`, `/navigation`, `/shift`                       | Field work                                   |
| `/wallet`, `/earnings`, `/performance`, `/vehicle`, `/documents`                                  | Capacity partner                             |
| `/communications`, `/support`, `/emergency`, `/insurance`, `/training`, `/profile`, `/onboarding` | Care / compliance                            |

**ARCH contract:** Do not unify BFF cookie path with mobile Bearer.

### 2.5 Website (`website` :3000)

Quote/book/track CTAs · locale SEO leaves · trust · contact · integrations education · vehicle pages · visitor session handoff into customer/book. Google Places on quote/book only.

### 2.6 Mobile

| App               | Screens / depth                                                                                                                |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `mobile-driver`   | SignIn · Jobs · JobDetail · Route · Inbox · Money · Docs · Onboarding · Support · More · ForceUpdate · Invite + `handshake.ts` |
| `mobile-customer` | Sign-in + Track shell (deeper product = intentional skip)                                                                      |

CI: no `:8000`, no Fleetbase HTTP, no SocketCluster in `apps/mobile-*/src`.

---

## 3. VROOM spine (`VR-*`) — deepest

**Existing seeds:** `services/fleetbase-adapter/tests/test_orchestrator.py`, `apps/api/tests/test_optimize_run_queue.py`, `test_orchestrator_ops.py`, `test_step2_optimize_enqueue.py`, `test_import_route_optimize.py`, `test_offline_optimize_route.py`, `test_phase4_interleaved_pudo.py`, `test_dispatch_processor.py`, worker `_optimize_run`.

| ID     | P   | Case                                                                                                                           |
| ------ | --- | ------------------------------------------------------------------------------------------------------------------------------ |
| VR-001 | P0  | Compose `vroom` healthy; `VROOM_ROUTER=valhalla`; depends on Valhalla; image pin not `:latest`                                 |
| VR-002 | P0  | Sidecar `:8030/health` returns OK when bridge on                                                                               |
| VR-003 | P0  | `_probe_vroom` posts allocate with `options.engine=vroom` via adapter `RUN_PATH` — never a PC-owned VROOM URL under `*_engine` |
| VR-004 | P0  | Bridge off → probe reports skipped healthy (not critical)                                                                      |
| VR-005 | P0  | Adapter not enabled → probe skipped                                                                                            |
| VR-006 | P1  | Verso SaaS “Invalid API Key” → warning with local topology hint (binary mode), not false-critical                              |
| VR-007 | P0  | `normalize_run_result` flattens assignments / unassigned / metrics (distance_m, duration_s, utilization)                       |
| VR-008 | P0  | Nested `plan.assignments` still normalizes                                                                                     |
| VR-009 | P0  | Engine error body without assignments → `ok:false` + hint                                                                      |
| VR-010 | P0  | Capacity reject reasons counted in `capacity_reject_count`                                                                     |
| VR-011 | P0  | Admin `OrchestratorOpsService.enqueue_run` does **not** call adapter synchronously                                             |
| VR-012 | P0  | Enqueue with no synced Fleetbase order IDs → skip queue                                                                        |
| VR-013 | P0  | Enqueue with no synced vehicles → skip queue                                                                                   |
| VR-014 | P0  | `execute_queued_run` writes ready status + assignments                                                                         |
| VR-015 | P0  | `run` passes Fleetbase vehicle public IDs to adapter                                                                           |
| VR-016 | P0  | Commit path creates manifests via `COMMIT_PATH` (adapter); PC UI does not write Fleetbase MySQL                                |
| VR-017 | P1  | Engines listing degrades when `/int/v1/fleet-ops/orchestrator/engines` unavailable                                             |
| VR-018 | P0  | Admin OptimizePanel: run → poll status → preview metrics → commit / discard                                                    |
| VR-019 | P0  | Merchant route import optimize enqueues worker job; NN + quote in worker, not sync POST                                        |
| VR-020 | P1  | Offline / circuit-open: enqueue fails closed with actionable error; no silent fake assignments                                 |
| VR-021 | P0  | Worker `_optimize_run` applies sequence for PC driver when commit confirms                                                     |
| VR-022 | P1  | Interleaved PUDO / remaining reoptimize via driver-platform `DriverRouteOptimizer`                                             |
| VR-023 | P0  | **Anti-case:** grep/CI — no `vroom` HTTP client import under `apps/api/src/porterchain_api/*_engine`                           |
| VR-024 | P0  | **Anti-case:** Route Center / PC TSP flags stay retired (`Phase2Flags.route_center` false)                                     |
| VR-025 | P1  | Fuel scorecard enrichment on optimize result does not call Google                                                              |
| VR-026 | P2  | CUOPT shadow (if flagged) never replaces VROOM commit path                                                                     |
| VR-027 | P1  | Diagnostics System Center surfaces VROOM probe result alongside Fleetbase probe                                                |
| VR-028 | P2  | Empty allocate probe latency recorded; keys truncated safely                                                                   |

---

## 4. Fleetbase handshake (`FB-*`)

**Existing seeds:** `services/fleetbase-adapter/tests/test_contract.py`, `test_client_timeout_breaker.py`, `test_mappers.py`, `test_manifests.py`, `test_tracking_playback.py`, `apps/api/tests/test_fleetbase_*`, `test_retry_queue_phase1.py`, `services/test_booking_sync_phase2.py`.

| ID     | P   | Case                                                                                               |
| ------ | --- | -------------------------------------------------------------------------------------------------- |
| FB-001 | P0  | `FleetbaseClient.request` auth header + base URL from settings                                     |
| FB-002 | P0  | Timeout opens circuit; subsequent calls raise `FleetbaseCircuitOpenError`                          |
| FB-003 | P0  | Booking → `BookingSyncService` creates/updates Fleetbase order IDs                                 |
| FB-004 | P0  | Sync failure → `RetryQueue` / `FleetbaseSyncJob`; worker drains                                    |
| FB-005 | P0  | Webhook signature verify → `WebhookProcessor.process` status translate                             |
| FB-006 | P0  | Status translator maps Fleetbase → `OrderState` without inventing states                           |
| FB-007 | P0  | POD download / mapping via adapter `pod` module                                                    |
| FB-008 | P0  | Live GPS SoT remains Fleetbase; Redis last-known is cache with CAS by `recorded_at`                |
| FB-009 | P0  | Ops mirror / breadcrumbs via adapter REST — web never SocketCluster                                |
| FB-010 | P0  | Portals never call Fleetbase `:8000` HTTP (guard `verify_vendor_leaves` / architecture boundaries) |
| FB-011 | P1  | Admin does **not** launch Fleetbase Ember console — bond is API `:8000` via adapter                |
| FB-012 | P1  | Merchant sync validation errors surface as booking validation, not 500 dump                        |
| FB-013 | P0  | Driver façade (`driver_engine`) reads online/availability via adapter — no PC reinvent             |
| FB-014 | P1  | Public tracking snapshot uses Maps + mirrored state; no Fleetbase token in browser                 |
| FB-015 | P2  | Manifest create/list contract tests stay green                                                     |
| FB-016 | P1  | Webhook retry / idempotency on duplicate delivery                                                  |
| FB-017 | P0  | Integration bridge `get_fleetbase_integration` respects `fleetbase_dispatch_bridge`                |
| FB-018 | P2  | Zones / vehicles / drivers module wrappers return typed errors                                     |

---

## 5. Maps · Valhalla · OSRM · Google (`MAP-*`)

**Existing seeds:** `services/python/tests/test_valhalla_costing.py`, `test_polyline.py`, `apps/api/tests/test_live_map.py`, `test_assignment_scoring.py`, `test_public_tracking_snapshot.py`, pricing FSA/GTA tests.

| ID      | P   | Case                                                                                                                                    |
| ------- | --- | --------------------------------------------------------------------------------------------------------------------------------------- |
| MAP-001 | P0  | Valhalla `:8002` route healthy on GTA ±150 km extract                                                                                   |
| MAP-002 | P0  | OSRM `:5000` same PBF extract; `osrm-routed` serves `gta-150km.osrm`                                                                    |
| MAP-003 | P0  | `MapsService.route_with_source` prefers Valhalla; falls back OSRM when Valhalla down                                                    |
| MAP-004 | P0  | Engines call only public Maps APIs (`route`, `matrix_durations`, `eta_between`, `optimized_route`, …) — never `_osrm_*` / `_valhalla_*` |
| MAP-005 | P0  | Quote distance via `resolve_route_distance` — Valhalla/OSRM only                                                                        |
| MAP-006 | P0  | Costing selector: box vs auto vehicle classes                                                                                           |
| MAP-007 | P0  | `osrm_allow_public_demo` default false; public demo last-resort labeled                                                                 |
| MAP-008 | P0  | CI fails unlabeled `router.project-osrm.org` default                                                                                    |
| MAP-009 | P0  | Google Places autocomplete on book/quote UX works                                                                                       |
| MAP-010 | P0  | **Anti-case:** no Google Distance Matrix / Directions for pricing or dispatch                                                           |
| MAP-011 | P1  | Live map panel ETA uses MapsService, not haversine as SoT (haversine UI must be labeled approx)                                         |
| MAP-012 | P1  | Isochrone / matrix for control-tower scoring shapes correct                                                                             |
| MAP-013 | P2  | Polyline encode/decode round-trip                                                                                                       |
| MAP-014 | P1  | Out-of-GTA coordinates fail closed with coverage error (not silent public OSRM)                                                         |
| MAP-015 | P2  | `tune-valhalla-json.py` still produces valid config for 4GB hosts                                                                       |

---

## 6. FastAPI / OpenAPI / engines (`API-*` / `ENG-*`)

**Census:** 639 ops / 568 paths — `docs/api/openapi.json`; guard `scripts/openapi_census.py`.

| ID      | P   | Case                                                                                                                                                    |
| ------- | --- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| API-001 | P0  | `/health` / readiness include Valhalla/OSRM reachability flags                                                                                          |
| API-002 | P0  | Persona prefixes enforced: `/v1/admin`, `/v1/merchant`, `/v1/merchant-api`, `/driver-api/v1`, `/v1/quotes`, `/v1/bookings`, public track, `/webhooks/*` |
| API-003 | P0  | Cut endpoints stay gone (`POST /driver/location`, banned tracking aliases)                                                                              |
| API-004 | P0  | New untagged business path fails census CI                                                                                                              |
| API-005 | P0  | Routers: auth + `require_module` + one service call (no new inline `BaseModel`)                                                                         |
| API-006 | P0  | IDOR: merchant A cannot read merchant B order/invoice/route job                                                                                         |
| API-007 | P0  | Staff session required for `/v1/admin/*`; Clerk org for merchant; Clerk Bearer for driver-api                                                           |
| API-008 | P1  | Partner `/v1/merchant-api` API key + idempotency replay                                                                                                 |
| API-009 | P0  | Webhook routes verify signatures (Clerk / Stripe / Fleetbase)                                                                                           |
| API-010 | P1  | Rate limit middleware on gateway paths                                                                                                                  |
| ENG-001 | P0  | Model ownership: writes only in owning engine (`verify_model_ownership.py`)                                                                             |
| ENG-002 | P0  | No ops spatial math in admin_engine (`verify_no_ops_spatial_math.py`)                                                                                   |
| ENG-003 | P0  | Cross-engine import freeze / D2 contracts                                                                                                               |
| ENG-004 | P1  | Thin-router logic allowlist remains 0                                                                                                                   |
| ENG-005 | P1  | Fat-but-coherent files not vanity-split (`shopify_service`, `settings_service`, `schemas_admin`, `routers/merchants`)                                   |

Key engine smoke (one happy path each): `booking_engine` quote→pay→confirm; `merchant_engine` book + route import; `admin_engine` operations enqueue; `pricing_engine` FSA/GTA; `billing_engine` invoice/COD policy; `fleetbase_engine` sync+webhook; `driver_engine` jobs façade; `notification_engine` deliver; `support_engine` claim/ticket; `compliance_engine` privacy DSR; `collaboration_engine` CRM contact.

---

## 7. Worker / EventBus (`WK-*`)

| ID     | P   | Case                                                                  |
| ------ | --- | --------------------------------------------------------------------- |
| WK-001 | P0  | Worker drains optimize queue after enqueue                            |
| WK-002 | P0  | Fleetbase retry queue drain + dead-letter visibility                  |
| WK-003 | P0  | Domain events catalog names stable (`DomainEventType`)                |
| WK-004 | P1  | Dispatch processor assigns without inventing GPS store                |
| WK-005 | P1  | Notification async delivery; failure recorded on `NotificationRecord` |
| WK-006 | P2  | Queue name constants match Redis prefixes                             |
| WK-007 | P1  | Lead nurture / CAPI async jobs fail closed                            |

---

## 8. Admin UI / UX (`A-UI-*`)

| ID       | P   | Case                                                                                        |
| -------- | --- | ------------------------------------------------------------------------------------------- |
| A-UI-001 | P0  | Unauthenticated `/operations` redirects to staff sign-in                                    |
| A-UI-002 | P0  | Control Tower loads board + KPI strip without calling Fleetbase from browser                |
| A-UI-003 | P0  | OptimizePanel end-to-end against queued run (mock adapter OK in unit; live in system-tests) |
| A-UI-004 | P0  | Live map tiles Google; positions from PC API (adapter-fed)                                  |
| A-UI-005 | P0  | Assign driver modal → admin API → Fleetbase assign via adapter                              |
| A-UI-006 | P1  | Exceptions tab + reason modal persists exception                                            |
| A-UI-007 | P1  | Order assist propose → confirm only; no auto Valhalla/Fleetbase/Stripe writes               |
| A-UI-008 | P1  | PushHealthStrip reflects FCM/email SLI                                                      |
| A-UI-009 | P0  | Settings panels: env-owned read-only; writable keys via bindings                            |
| A-UI-010 | P0  | Project mode immutable in UI (`403 project_mode_immutable`)                                 |
| A-UI-011 | P1  | System-health shows VROOM + Valhalla + OSRM + Mailpit + Redis + Postgres probes             |
| A-UI-012 | P1  | Merchant 360 pricing / GTA matrix fields save via admin merchant org                        |
| A-UI-013 | P1  | Finance invoice detail record payment / remind pay link                                     |
| A-UI-014 | P2  | Blog CRUD                                                                                   |
| A-UI-015 | P1  | Leads pipeline drag/status + calendar                                                       |
| A-UI-016 | P0  | RBAC: role cannot open modules outside SpiceDB/module matrix                                |
| A-UI-017 | P1  | Realtime notifications via staff WS token — not SocketCluster                               |
| A-UI-018 | P2  | Ops command palette keyboard navigation                                                     |
| A-UI-019 | P1  | Dispatcher copilot read-only tools; no write tools to maps/Fleetbase/Stripe                 |
| A-UI-020 | P0  | Admin nav groups match live routes (no orphan top-level pages)                              |

---

## 9. Merchant UI (`M-UI-*`)

| ID       | P   | Case                                                                        |
| -------- | --- | --------------------------------------------------------------------------- |
| M-UI-001 | P0  | Sign-in / org switcher memberships                                          |
| M-UI-002 | P0  | Book flow quote parity with API breakdown                                   |
| M-UI-003 | P0  | Routes upload CSV → mapping profile → optimize enqueue → job status page    |
| M-UI-004 | P0  | Orders board cancel/duplicate owned only                                    |
| M-UI-005 | P0  | Shopify connect page OAuth + shop record                                    |
| M-UI-006 | P0  | API keys mint on merchant; admin can revoke only                            |
| M-UI-007 | P1  | Billing overview AR + remittance pack                                       |
| M-UI-008 | P1  | Tracking / print / POD download                                             |
| M-UI-009 | P1  | Team invite / role seat sync CRM contact                                    |
| M-UI-010 | P1  | Settings: locations, tax, branding, alert prefs (not invoices/keys/Shopify) |
| M-UI-011 | P2  | Referrals credits ledger                                                    |
| M-UI-012 | P1  | Reports spend attribution                                                   |
| M-UI-013 | P0  | Activation / first-run gates before book                                    |
| M-UI-014 | P1  | Bulk upload template + idempotent job                                       |

---

## 10. Driver web + mobile (`D-UI-*` / `MOB-*`)

| ID       | P   | Case                                                                        |
| -------- | --- | --------------------------------------------------------------------------- |
| D-UI-001 | P0  | BFF `/api/driver` proxies to `/driver-api/v1` with session                  |
| D-UI-002 | P0  | Jobs list / detail / navigation pages load assigned only                    |
| D-UI-003 | P1  | Wallet / earnings / documents feature flags                                 |
| D-UI-004 | P1  | Verification CTAs on web (Identity/Checkr/Abstract) when flags on           |
| MOB-001  | P0  | Handshake probes `:8001` before field session                               |
| MOB-002  | P0  | Clerk Bearer on driver API                                                  |
| MOB-003  | P0  | FCM token register → notification_engine                                    |
| MOB-004  | P0  | Location ping path uses approved driver-api (not banned `/driver/location`) |
| MOB-005  | P0  | **Anti-case:** no Fleetbase/SocketCluster imports in mobile src             |
| MOB-006  | P1  | Route screen sequence from optimize commit                                  |
| MOB-007  | P2  | Force-update gate                                                           |
| MOB-008  | P3  | Customer mobile beyond Sign-in+Track (intentional skip — do not fail CI)    |

---

## 11. Website (`W-UI-*`)

| ID       | P   | Case                                                     |
| -------- | --- | -------------------------------------------------------- |
| W-UI-001 | P0  | Quote CTA → Places → `/v1/quotes` distance Valhalla/OSRM |
| W-UI-002 | P0  | Book continue / success handoff visitor session          |
| W-UI-003 | P0  | Public track page                                        |
| W-UI-004 | P1  | Charter: no Phase 3 sold as today on customer paths      |
| W-UI-005 | P2  | Locale routing / hreflang / sitemap entries              |
| W-UI-006 | P1  | Contact / lead ingest webhook                            |
| W-UI-007 | P2  | Trust / legal pages render                               |

---

## 12. Auth · Clerk · SpiceDB · staff IdP (`AUTH-*`)

| ID       | P   | Case                                                                   |
| -------- | --- | ---------------------------------------------------------------------- |
| AUTH-001 | P0  | `CLERK_<PORTAL>_*` triad from `env/clerk.env` + `pnpm clerk:sync`      |
| AUTH-002 | P0  | Local `CLERK_DEV_BYPASS` / `NEXT_PUBLIC_CLERK_DEV_BYPASS` Bearer `dev` |
| AUTH-003 | P0  | **Anti-case:** no `ADMIN_CLERK_SECRET_KEY` ad-hoc names                |
| AUTH-004 | P0  | Staff IdP session cookie → `/v1/admin`; not Firebase Auth              |
| AUTH-005 | P0  | SpiceDB Check — no caching allows                                      |
| AUTH-006 | P0  | Persona bundle load for merchant/driver/customer                       |
| AUTH-007 | P1  | Invitation flows (staff/merchant/driver)                               |
| AUTH-008 | P1  | Step-up / passkey enrollment on admin security                         |
| AUTH-009 | P0  | Webhook Clerk user sync / rebind via identity links                    |
| AUTH-010 | P1  | Hybrid RBAC module matrix tests green                                  |
| AUTH-011 | P0  | Tenant access: org membership required                                 |

---

## 13. Stripe · billing · finance (`PAY-*`)

**Deep catalog (admin Finance tabs, merchant Billing/Reports, Fleetbase POD→invoice, all layers):** [FINANCE_INVOICE_REPORTS_DEV_TEST_CASES.md](FINANCE_INVOICE_REPORTS_DEV_TEST_CASES.md).

| ID      | P   | Case                                                     |
| ------- | --- | -------------------------------------------------------- |
| PAY-001 | P0  | Retail Checkout happy path + webhook idempotency         |
| PAY-002 | P0  | Only `porterchain_services/stripe/sdk.py` imports stripe |
| PAY-003 | P0  | COD Connect / Payment Link additive — Checkout unbroken  |
| PAY-004 | P1  | Invoice PDF/CSV cents; remind pay link                   |
| PAY-005 | P1  | Merchant AR generate / pay / one AR total                |
| PAY-006 | P1  | Credit notes / collections queue                         |
| PAY-007 | P1  | Driver payout wallet ledger ownership in `driver_engine` |
| PAY-008 | P2  | Shopify billing wave remaining cases                     |
| PAY-009 | P0  | Webhook signature fail → 4xx, no state change            |

---

## 14. Notifications · email · FCM (`NOTIF-*`)

| ID        | P   | Case                                                 |
| --------- | --- | ---------------------------------------------------- |
| NOTIF-001 | P0  | Mailpit receives booking/confirmation email in local |
| NOTIF-002 | P1  | ZeptoMail HTTPS path in non-local (mocked unit)      |
| NOTIF-003 | P0  | FCM device token upsert; push delivery record        |
| NOTIF-004 | P0  | Admin Firebase messaging SW registers                |
| NOTIF-005 | P1  | Loud push / ops notification SLI metrics             |
| NOTIF-006 | P1  | Inbox unread / mark read per persona                 |
| NOTIF-007 | P0  | **Anti-case:** no second mail/FCM engine             |
| NOTIF-008 | P2  | Preference opt-outs respected                        |

---

## 15. Shopify · partner API · ERP-shaped (`SHOP-*` / `INT-*`)

| ID       | P   | Case                                                                                                                                                                   |
| -------- | --- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SHOP-001 | P0  | OAuth install → `ShopifyShop` row                                                                                                                                      |
| SHOP-002 | P0  | Carrier rates handshake uses PC pricing (Valhalla distance), not Google                                                                                                |
| SHOP-003 | P0  | Order ingest → merchant booking path                                                                                                                                   |
| SHOP-004 | P1  | Rate quote persistence / webhook env sandbox flag                                                                                                                      |
| SHOP-005 | P2  | URL helpers / phase4 remaining                                                                                                                                         |
| INT-001  | P0  | `/v1/merchant-api` idempotency key replay                                                                                                                              |
| INT-002  | P0  | Merchant outbound webhooks signed delivery                                                                                                                             |
| INT-003  | P1  | OAuth third-party client list/create                                                                                                                                   |
| INT-004  | P1  | Bulk/CSV import as ERP stand-in (mapping profiles, errors)                                                                                                             |
| INT-005  | P2  | Standing orders schedule runs                                                                                                                                          |
| INT-006  | P3  | External ERP (NetSuite/SAP/etc.) — **not in repo**; treat CSV + Shopify + merchant-api as the supported edges until a registered adapter exists in `integrations.yaml` |

---

## 16. CRM · leads · support · claims (`CRM-*`)

| ID      | P   | Case                                                 |
| ------- | --- | ---------------------------------------------------- |
| CRM-001 | P0  | Lead ingest bus + settings                           |
| CRM-002 | P1  | Lead scoring / merge / nurture                       |
| CRM-003 | P1  | Channel webhooks / CAPI                              |
| CRM-004 | P0  | Support ticket create → timeline                     |
| CRM-005 | P0  | Claims create/update via support_engine              |
| CRM-006 | P2  | Blog / content ops                                   |
| CRM-007 | P1  | Convert lead → merchant/customer without hard-DELETE |

---

## 17. Database · models · migrations (`DB-*`)

| ID     | P   | Case                                                      |
| ------ | --- | --------------------------------------------------------- |
| DB-001 | P0  | Alembic upgrade head on empty Postgres 18                 |
| DB-002 | P0  | Postgres smoke + CRM JSON queries                         |
| DB-003 | P0  | Integrity FKs migration holds                             |
| DB-004 | P0  | Import `booking_models` — deleted `models.py` stays gone  |
| DB-005 | P1  | Order / Payment / Invoice cents invariants                |
| DB-006 | P1  | NotificationRecord / FleetbaseSyncJob indexes usable      |
| DB-007 | P2  | Referral credits / wallet package migrations              |
| DB-008 | P1  | `is_sandbox` is traffic label — not platform project mode |

---

## 18. Docker · infra · compose (`DOC-*`)

| ID      | P   | Case                                                                                                                      |
| ------- | --- | ------------------------------------------------------------------------------------------------------------------------- |
| DOC-001 | P0  | Images exact tag/digest — never `:latest` for Valhalla/OSRM/VROOM/Mailpit                                                 |
| DOC-002 | P0  | Profiles: core vs fleetbase                                                                                               |
| DOC-003 | P0  | Ports: API 8001 · Valhalla 8002 · OSRM 5000 · VROOM/sidecar 8030 · Mailpit · Redis 8.8 · Postgres 18 · Fleetbase Valkey 8 |
| DOC-004 | P0  | Mailpit not Mailhog                                                                                                       |
| DOC-005 | P0  | Fleetbase MySQL separate from PC Postgres                                                                                 |
| DOC-006 | P1  | `prepare-valhalla-gta.sh` / `prepare-osrm-gta.sh` docs match extract (not full Ontario)                                   |
| DOC-007 | P1  | `fleetbase-verify.sh` compose helper                                                                                      |
| DOC-008 | P2  | Worker + API share compatible env from `env/*.example`                                                                    |
| DOC-009 | P0  | VROOM depends_on Valhalla healthy                                                                                         |

---

## 19. Architecture / CI contracts (`ARCH-*`)

| ID       | P   | Case                                                                                 |
| -------- | --- | ------------------------------------------------------------------------------------ |
| ARCH-001 | P0  | `verify_architecture_boundaries.py`                                                  |
| ARCH-002 | P0  | `verify_vendor_leaves.py` (OSRM URL, VROOM leaf, mobile Fleetbase ban)               |
| ARCH-003 | P0  | `verify_integrations_matrix.py` ↔ `integrations.yaml`                                |
| ARCH-004 | P0  | `openapi_census.py`                                                                  |
| ARCH-005 | P0  | `verify_model_ownership.py`                                                          |
| ARCH-006 | P0  | `verify_no_ops_spatial_math.py`                                                      |
| ARCH-007 | P1  | `verify_doc_governance.py` / pointer stubs                                           |
| ARCH-008 | P0  | Folder law: adapters vs engines vs thin routers                                      |
| ARCH-009 | P0  | Rejected overlays not reintroduced (`core/`, `backend/`, `personas/`)                |
| ARCH-010 | P1  | Graphify god-nodes still documented after folder-graph changes (`graphify update .`) |

---

## 20. Gaps you asked for + items you missed

Explicitly included above beyond the original list:

| Missed / easy to forget          | Why it matters                  | Prefix    |
| -------------------------------- | ------------------------------- | --------- |
| SpiceDB authz                    | Allow/deny is not Clerk         | AUTH      |
| Staff IdP (passkey/magic)        | Admin is not portal Clerk       | AUTH      |
| EventBus + worker                | Optimize/sync/notify are async  | WK        |
| Redis last-known GPS             | Cache, not SoT                  | FB/DB     |
| Fleetbase Valkey + MySQL         | Separate from PC Postgres/Redis | DOC       |
| ZeptoMail                        | Prod email path                 | NOTIF     |
| Nominatim / geocode fallback     | Server geocode when needed      | MAP       |
| Partner merchant-api + OAuth     | ERP-shaped edge                 | INT       |
| Lead ingest / Meta CAPI          | Growth bus                      | CRM       |
| Checkr / Stripe Identity         | Driver trust                    | D-UI/AUTH |
| Standing orders                  | Recurring capacity              | INT       |
| Referral credits                 | Merchant growth                 | M-UI      |
| COD Connect                      | Money additive                  | PAY       |
| OpenAPI census / verify_*        | Architecture as tests           | ARCH      |
| Project mode / Doppler boot      | Immutable APP_ENV               | A-UI/DOC  |
| Admin web FCM + WS token         | Ops loud push                   | NOTIF     |
| CUOPT shadow                     | Must not replace VROOM          | VR        |
| Visitor session website→customer | Retail handoff                  | W-UI      |
| Integrity FK alembic             | Data trust                      | DB        |
| Intentional skips as anti-cases  | Prevent false failures          | ARCH      |

**Not in repo as first-class adapters (do not invent greenfield tests as if shipped):** NetSuite, SAP, QuickBooks, Twilio SMS SoT, Mapbox routing, Firebase Auth, Google Distance Matrix, in-house VROOM.

---

## 21. Suggested execution order (dev layer)

1. **DOC + MAP + VR probes** — compose up; System Center green.
2. **AUTH + API census** — staff/merchant/driver tokens.
3. **PAY + booking loop** — quote→checkout→webhook→Fleetbase sync.
4. **FB sync + webhook** — order state round-trip.
5. **VR optimize enqueue→worker→commit** — Control Tower + merchant routes.
6. **NOTIF** — Mailpit + FCM register.
7. **SHOP/INT** — Shopify carrier + merchant-api idempotency.
8. **Portal UI smoke** — one path per persona page group.
9. **ARCH verify_*** — CI gates.
10. Persona-deep catalogs (customer sibling; then merchant/driver as separate living docs).

---

## 22. Follow-up sensor work (do not do in this Graphify session)

**Moment B — CodeGraph** (separate session):

```text
codegraph_explore "OrchestratorOpsService enqueue_run execute_queued_run"
codegraph_explore "MapsService route_with_source matrix_durations"
codegraph_explore "normalize_run_result RUN_PATH COMMIT_PATH"
```

Extract Pydantic/ORM fields for optimize run status, assignment rows, quote distance sources.

**Moment C — Ripwire** (separate session):

```bash
ripwire . --cache=.ripwire --for="VROOM optimize enqueue via Fleetbase orchestrator"
ripwire . --cache=.ripwire --callers=OrchestratorOpsService
ripwire . --cache=.ripwire --expand=FleetbaseClient
ripwire . --cache=.ripwire --impact=MapsService
```

Use output to attach file:line owners to any new pytest modules.

---

## 23. Related

- [ARCHITECTURE.md](../ARCHITECTURE.md) — trunk + VROOM leaf rule
- [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md) — Use/Extend/Replace
- [INTEGRATIONS.md](../INTEGRATIONS.md) · [`integrations.yaml`](../integrations.yaml)
- [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)
- [FINANCE_INVOICE_REPORTS_DEV_TEST_CASES.md](FINANCE_INVOICE_REPORTS_DEV_TEST_CASES.md) — Finance Center · invoices · AR · merchant billing/reports · Fleetbase POD→invoice
- [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)
- [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md)
- [FLEETBASE_PERMANENT_BOND.md](FLEETBASE_PERMANENT_BOND.md) — PorterChain↔Fleetbase permanent bond
- [MERCHANT_DEVELOPMENT_TEST_MATRIX.md](MERCHANT_DEVELOPMENT_TEST_MATRIX.md)
- [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)
- Existing pytest: `apps/api/tests/test_optimize_run_queue.py`, `test_orchestrator_ops.py`, `services/fleetbase-adapter/tests/test_orchestrator.py`
