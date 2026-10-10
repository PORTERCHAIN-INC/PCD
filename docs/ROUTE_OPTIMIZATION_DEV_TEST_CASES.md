# Route optimization — development test cases

**Status:** living catalog for local/CI development (not prod Doppler validation).  
**Mapped:** 2026-09-17 via Graphify (`query` / `explain` / `path`) → CodeGraph CLI `explore` → Ripwire (`--for` / `--expand` / `--impact`).  
**Architecture SSOT:** [ARCHITECTURE.md](../ARCHITECTURE.md) Branch — spatial black boxes · Branch — execution (Fleetbase).  
**Charter:** Optimize **network capacity utilization**, not a second TSP product. VROOM stays behind Fleetbase; PorterChain never grows a VROOM HTTP client.

### Sensor trail (this pass)

| Moment | Tool          | What it named                                                                                                                                                                             |
| ------ | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A      | Graphify      | `OptimizePanel`, `OrchestratorOpsService`, `MapsService.optimized_route`, VROOM probe rationale, `MerchantRouteImportService.optimize`, `DriverRouteOptimizer`                            |
| B      | CodeGraph CLI | Commit chain `OrchestratorOpsService.commit` → `commit_orchestrator` → Fleetbase `OrchestratorService`; schemas `OptimizeRunBody`; blast radius on `MapsService` / driver jobs            |
| C      | Ripwire       | Thin router `optimize_run` → `_orch.enqueue_run`; impact radius 63 symbols (worker, driver accept/undo, fuel tools, offline executor); Shopify carrier + merchant bulk optimize neighbors |

**Existing coverage seed (do not duplicate blindly):**

| File                                                    | Focus                                                        |
| ------------------------------------------------------- | ------------------------------------------------------------ |
| `apps/api/tests/test_optimize_commit_p0.py`             | **P0 commit idempotency, CAS→409, undo**                     |
| `apps/api/tests/test_optimize_rbac_idor.py`             | **dispatch RBAC + driver cross-run IDOR**                    |
| `apps/admin/e2e/optimize.p0.spec.ts`                    | **UI-OPS-006 OptimizePanel smoke (mocked BFF)**              |
| `apps/api/tests/test_optimize_run_queue.py`             | Enqueue without adapter; synced fleet gates; execute → ready |
| `apps/api/tests/test_orchestrator_ops.py`               | Fleetbase id resolution helpers                              |
| `apps/api/tests/test_step2_optimize_enqueue.py`         | Driver/merchant enqueue; no in-process TSP                   |
| `apps/api/tests/test_import_route_optimize.py`          | Drop-order / sequence import shim                            |
| `apps/api/tests/test_gps_ingest_wave4.py`               | `DriverRouteOptimizer` does not build local TSP              |
| `apps/api/tests/test_remaining_to_live_prove.py`        | Handler enqueues without solver                              |
| `apps/api/tests/test_offline_optimize_route.py`         | Offline queue alias / preview flag                           |
| `apps/api/tests/test_fuel_scorecard.py`                 | Fuel metrics on optimize plan                                |
| `apps/api/tests/test_phase5c_baseline_events.py`        | `optimize.enqueued` events                                   |
| `apps/api/tests/test_phase5_ops_hardening.py`           | Sequence apply / conflict / rollback                         |
| `apps/api/tests/test_phase_ui_driver_preview.py`        | Preview→Accept apply_on_ready                                |
| `services/fleetbase-adapter/tests/test_orchestrator.py` | Adapter orchestrator contract                                |
| `services/python/tests/test_valhalla_costing.py`        | Vehicle-class costing                                        |
| `scripts/verify_no_ops_spatial_math.py`                 | Ban haversine/TSP in ops engines                             |
| `scripts/verify_vendor_leaves.py`                       | No PC VROOM client; local OSRM default                       |

---

## 0. ID scheme & layers

| Prefix    | Layer                                                        |
| --------- | ------------------------------------------------------------ |
| `A-UI-*`  | Admin Operations UI `:3002` — all ops tabs touching optimize |
| `M-UI-*`  | Merchant portal route import / bulk optimize                 |
| `D-UI-*`  | Driver web portal `:3003` optimize UX                        |
| `D-MOB-*` | Driver Expo `JobsScreen` / `RouteScreen` / handshake         |
| `API-A-*` | Staff `/v1/admin/.../optimize/*`                             |
| `API-D-*` | Driver `/driver-api/v1/jobs/optimize*`                       |
| `API-M-*` | Merchant `/v1/merchant/.../route-imports/.../optimize`       |
| `API-S-*` | Shopify carrier rates (distance handshake, not VROOM)        |
| `ENG-*`   | `OrchestratorOpsService`, import/jobs, maps                  |
| `MAP-*`   | `MapsService` Valhalla → OSRM → labeled public demo          |
| `FB-*`    | Fleetbase adapter + VROOM orchestrator                       |
| `VRM-*`   | Local `porterchain-vroom` + `VROOM_ROUTER=valhalla`          |
| `AUTH-*`  | Staff IdP / Clerk driver-merchant / RBAC `dispatch`          |
| `EVT-*`   | EventBus optimize.* / route.optimized                        |
| `WRK-*`   | Worker `dispatch.py` `_optimize_run` / `_optimize_import`    |
| `NOTIF-*` | FCM / email / Mailpit / admin push health after apply        |
| `SEQ-*`   | Driver sequence store CAS / conflict 409                     |
| `FUEL-*`  | Fuel scorecard / delta vs plan                               |
| `DB-*`    | Models / sync ids / BulkImportJob optimize fields            |
| `DOC-*`   | Docker compose Valhalla/OSRM/VROOM/Fleetbase                 |
| `ARCH-*`  | Ownership laws, OpenAPI census, sensor CI guards             |
| `INT-*`   | Shopify / partner API / ERP / website (adjacent)             |
| `DIAG-*`  | Diagnostics VROOM probe / integration health                 |

**Priority:** P0 = ship-blocker · P1 = trust/utilization/money · P2 = polish/regression · P3 = shadow/future.

Each case: **Precondition → Steps → Expected → Layer tags**.

---

## 1. Surface inventory (SSOT for “every page / file”)

### 1.1 Admin Operations (`apps/admin`) — `/operations`

| Tab / sub-surface      | Files                                        | Optimize relevance                                    |
| ---------------------- | -------------------------------------------- | ----------------------------------------------------- |
| Shell + tabs           | `app/(ops)/operations/page.tsx`              | Tab `optimize`; refresh after commit                  |
| **Optimize**           | `components/operations/OptimizePanel.tsx`    | Pool / run / poll / commit / discard                  |
| Overview               | same page + `KpiStrip`, `PushHealthStrip`    | Post-commit KPI / push health                         |
| Dispatch Board         | `DispatchBoard.tsx`                          | Assignments appear after commit                       |
| Live Map               | `LiveMapPanel.tsx`                           | Geometry via MapsService (not Google routing)         |
| Orders table           | `OrdersTablePanel.tsx`                       | Open order from optimize assignments                  |
| Dispatch Queue         | `DispatchQueuePanel.tsx`                     | Synced pool prerequisite                              |
| Scheduled batches      | `ScheduledBatchesPanel.tsx`                  | Batch vs ad-hoc optimize interaction                  |
| Utilization            | `UtilizationPanel.tsx`                       | Utilization after apply                               |
| Exceptions / SLA       | page tabs                                    | Unassigned / SLA after bad plan                       |
| AI Copilot             | `DispatcherCopilotPanel.tsx`                 | May read optimize run tools                           |
| Live Activity          | `ActivityTab`                                | `optimize.*` activity rows                            |
| Client lib             | `lib/operations.ts`                          | `OptimizeRunResult`, `optimizePool/Run/Status/Commit` |
| Auth                   | `AdminAuthProvider`, staff session / step-up | Token for optimize APIs                               |
| Settings / diagnostics | `SystemCenter`, Integration panel            | Fleetbase + VROOM health                              |

### 1.2 Merchant portal

| Surface                          | Files                                                             |
| -------------------------------- | ----------------------------------------------------------------- |
| Bulk / route import              | `components/bulk/BulkUploadClient.tsx` (`onOptimize`)             |
| API client                       | `lib/api.ts` → `optimizeRouteImport`                              |
| Routes list (adjacent)           | `components/routes/RouteList.tsx`, `app/(portal)/routes/page.tsx` |
| Shopify parse (feed into import) | `lib/route-module/shopifyParser.ts`, types                        |

### 1.3 Driver web + mobile

| Surface         | Files                                                                                        |
| --------------- | -------------------------------------------------------------------------------------------- |
| Driver web jobs | `apps/driver-portal/src/lib/jobs.ts`, telemetry `optimizeEngineNote`                         |
| Mobile jobs     | `apps/mobile-driver/src/screens/JobsScreen.tsx` (preview / accept / undo / offline)          |
| Mobile route    | `RouteScreen.tsx`, `handshake.ts`, `useEnterRoute`, `gate.ts`                                |
| Platform        | `services/driver-platform/porterchain_driver/{jobs,route_optimizer,stops,sequence_store}.py` |

### 1.4 API routers (thin)

| Endpoint family | File                                | Handlers                                                                                                                   |
| --------------- | ----------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| Admin optimize  | `routers/operations.py`             | `optimize_pool`, `optimize_engines`, `optimize_run`, `optimize_run_status`, `optimize_commit` (+ live_map, playback, sync) |
| Driver optimize | `routers/driver/jobs.py`            | `POST /jobs/optimize`, `GET .../runs/{id}`, `POST .../accept`, `POST .../undo`                                             |
| Merchant import | `routers/merchant/route_imports.py` | `optimize_route_import`                                                                                                    |
| Shopify rates   | `routers/shopify.py`                | `shopify_carrier_service_rates` (Maps distance, **not** VROOM)                                                             |

### 1.5 Engines / adapters / maps

| Area                     | Path                                                                                                                        |
| ------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| Orchestrator ops         | `admin_engine/orchestrator_ops_service.py`                                                                                  |
| Optimize store / events  | `fleetbase_engine/optimize_run_store.py`, `optimize_events.py`                                                              |
| Merchant import          | `merchant_engine/route_import_service.py`, `import_jobs.py`                                                                 |
| Admin ops enqueue helper | `admin_engine/operations_service.py` `_enqueue_driver_book_optimize`                                                        |
| Maps                     | `services/python/porterchain_services/maps/{service,sequence,route_helpers}.py`                                             |
| Pricing façade           | `apps/api/.../services/routing.py` `resolve_route_distance`                                                                 |
| Fleetbase orchestrator   | `services/fleetbase-adapter/.../orchestrator/`, `integration.py`, `routes/`                                                 |
| Worker                   | `apps/worker/processors/dispatch.py`                                                                                        |
| Intelligence             | `intelligence_engine/tools.py` (`get_optimize_run`, fuel)                                                                   |
| Diagnostics              | `admin_engine/diagnostics_fleetbase_probes.py` `_probe_vroom`                                                               |
| Schemas                  | `schemas_admin.py` `OptimizeRunBody`, `OptimizeCommitBody`                                                                  |
| Models                   | `booking_models.Order`, `admin_models.Driver/Vehicle`, `merchant_models.BulkImportJob`, `fleetbase_models.FleetbaseSyncJob` |

### 1.6 Docker / infra

| Service                            | Compose                                         | Port / pin        |
| ---------------------------------- | ----------------------------------------------- | ----------------- |
| Valhalla                           | `porterchain-valhalla` digest-pinned            | `:8002`           |
| OSRM                               | `osrm-backend:v5.27.1` GTA ±150 km              | `:5000`           |
| VROOM                              | `vroom-docker:v1.14.0`, `VROOM_ROUTER=valhalla` | profile `routing` |
| Fleetbase                          | `:8000` + Valkey 8 override                     | orchestrator API  |
| API / worker / Redis / Postgres 18 | standard stack                                  | EventBus drain    |

### 1.7 Integrations in / adjacent to optimize

| System                     | Role in optimize                                                   |
| -------------------------- | ------------------------------------------------------------------ |
| **Fleetbase + VROOM**      | Only TSP/VRP SoT for dispatch apply                                |
| **Valhalla**               | Matrix/route for Maps + VROOM router                               |
| **OSRM**                   | Maps fallback ETA/distance                                         |
| **Google Maps**            | Places + tiles only — never optimize distance                      |
| **Clerk**                  | Merchant/driver Bearer; admin uses staff IdP                       |
| **Firebase FCM**           | Push after apply / job sequence change                             |
| **Email / Mailpit**        | Optional notify merchant/driver on plan apply                      |
| **Shopify**                | Carrier rates use Maps pricing path; bulk import can feed optimize |
| **Partner / merchant-api** | External ERP ingest → same import/optimize enqueue                 |
| **SpiceDB / RBAC**         | `dispatch` / `dispatch_read` modules on admin optimize             |

---

## 2. Admin Optimize UI (`A-UI-*`)

### 2.1 Tab shell `/operations` → Optimize

| ID       | P   | Case                                                                                                           |
| -------- | --- | -------------------------------------------------------------------------------------------------------------- |
| A-UI-001 | P0  | Staff with `dispatch_read` opens `/operations`, tab **Optimize** mounts `OptimizePanel` without console errors |
| A-UI-002 | P0  | Without dispatch module, Optimize APIs 403 and panel shows auth/error (no silent empty success)                |
| A-UI-003 | P1  | Switching away and back preserves or clears pending poll correctly (no leaked intervals)                       |
| A-UI-004 | P2  | After `onCommitted`, parent `refresh`/`tick` updates Board, Queue, Map, Activity                               |

### 2.2 Pool + shape controls

| ID       | P   | Case                                                                                      |
| -------- | --- | ----------------------------------------------------------------------------------------- |
| A-UI-010 | P0  | Pool loads: synced order/merchant/vehicle counts; empty pool shows actionable empty state |
| A-UI-011 | P0  | Shape `fleet` / `merchant` / `vehicle` toggles correct secondary selects                  |
| A-UI-012 | P0  | Merchant shape with no merchant selected → run blocked or clear validation error          |
| A-UI-013 | P0  | Vehicle shape requires vehicle id; sends `vehicle_ids: [id]`                              |
| A-UI-014 | P1  | Engine select `vroom` vs greedy labels match API (`Fleetbase VROOM` / greedy)             |
| A-UI-015 | P1  | Mode `allocate` (and any other allowed modes) round-trips to `OptimizeRunBody.mode`       |

### 2.3 Run / poll / ready / error

| ID       | P   | Case                                                                                   |
| -------- | --- | -------------------------------------------------------------------------------------- |
| A-UI-020 | P0  | Run → `status=pending` + `run_id` → poll every ~1s up to 45 → `ready` with assignments |
| A-UI-021 | P0  | Poll `optimize_run_not_found` early does not abort until `POLL_MAX`                    |
| A-UI-022 | P0  | `status=error` stops busy, shows `error`/`message`                                     |
| A-UI-023 | P0  | Timeout after max polls: “Preview timed out. Try again.” and clears runId              |
| A-UI-024 | P1  | Ready with **zero** assignments shows Fleetbase sync hint (vans online / live fb ids)  |
| A-UI-025 | P1  | Metrics strip renders distance/duration/fuel fields when present                       |
| A-UI-026 | P1  | Unassigned details list is readable; clicking assignment opens order via `onOpenOrder` |
| A-UI-027 | P2  | Discard clears plan/runId/error and stops poll                                         |

### 2.4 Commit

| ID       | P   | Case                                                                   |
| -------- | --- | ---------------------------------------------------------------------- |
| A-UI-030 | P0  | Commit disabled while `pending` or no assignments                      |
| A-UI-031 | P0  | Commit success clears plan and refreshes ops surfaces                  |
| A-UI-032 | P0  | Commit failure shows API error; plan retained unless sequence conflict |
| A-UI-033 | P0  | Sequence conflict message clears plan (force re-preview)               |
| A-UI-034 | P1  | Double-click commit does not double-apply (idempotent `run_id`)        |

### 2.5 Adjacent ops tabs (handshake UX)

| ID       | P   | Case                                                                |
| -------- | --- | ------------------------------------------------------------------- |
| A-UI-040 | P1  | Board reflects new driver↔order links after commit                  |
| A-UI-041 | P1  | Live Map route geometry updates without calling Google Directions   |
| A-UI-042 | P1  | Activity shows optimize.enqueued → ready → applied                  |
| A-UI-043 | P2  | Copilot can reference run via tools without writing a second solver |
| A-UI-044 | P2  | PushHealthStrip does not regress when optimize push fires           |
| A-UI-045 | P2  | Utilization / SLA tabs remain coherent after large fleet apply      |

### 2.6 UX / a11y

| ID       | P   | Case                                                         |
| -------- | --- | ------------------------------------------------------------ |
| A-UI-050 | P2  | Busy states disable Run/Commit; Spinner visible              |
| A-UI-051 | P2  | Keyboard reachable selects/buttons; errors announced         |
| A-UI-052 | P2  | Mobile viewport: shape/engine controls wrap without clipping |

---

## 3. Merchant UI (`M-UI-*`)

| ID       | P   | Case                                                                           |
| -------- | --- | ------------------------------------------------------------------------------ |
| M-UI-001 | P0  | Bulk upload job with ≥2 stops shows Optimize CTA when unconfirmed              |
| M-UI-002 | P0  | Optimize sets `optimize_status=pending`, polls until ready/applied/error       |
| M-UI-003 | P0  | Confirmed job cannot re-optimize (`_assert_unconfirmed`)                       |
| M-UI-004 | P1  | Optimize keeps pickup-first semantics (import matrix)                          |
| M-UI-005 | P1  | Shopify-parsed stop sheet can enter same optimize path                         |
| M-UI-006 | P2  | Routes list still lists jobs; no Fleetbase URL leaked to browser               |
| M-UI-007 | P2  | Error codes (`route_import_needs_two_stops`, mapping confidence) surface in UI |

---

## 4. Driver web + mobile (`D-UI-*`, `D-MOB-*`)

### 4.1 Driver web

| ID       | P   | Case                                                                          |
| -------- | --- | ----------------------------------------------------------------------------- |
| D-UI-001 | P0  | Optimize available only when jobs synced + `can_optimize`                     |
| D-UI-002 | P0  | Preview → accept → stop order updates; undo restores prior sequence           |
| D-UI-003 | P1  | Telemetry label `optimizeEngineNote` shows engine without promising PC solver |
| D-UI-004 | P1  | BFF `/api/driver` → `/driver-api/v1` never calls Fleetbase from browser       |

### 4.2 Mobile driver

| ID        | P   | Case                                                                          |
| --------- | --- | ----------------------------------------------------------------------------- |
| D-MOB-001 | P0  | JobsScreen Optimize builds preview; polls run status                          |
| D-MOB-002 | P0  | Accept with `sequence_version` CAS; conflict shows clear error                |
| D-MOB-003 | P0  | Undo after accept rolls back and emits rejected/rolled_back path              |
| D-MOB-004 | P0  | Offline: `enqueueOfflineAction("optimize_route")` queues; drains on reconnect |
| D-MOB-005 | P1  | Midday `reoptimize_remaining` after deliver_stop excludes completed stops     |
| D-MOB-006 | P1  | Handshake / `canEnterRoute` still gates RouteScreen independently of optimize |
| D-MOB-007 | P1  | Maps tiles/Places OK; navigation geometry not Google Directions for TSP       |
| D-MOB-008 | P2  | Preview stop list truncates safely (slice UI) without losing accept payload   |
| D-MOB-009 | P3  | Customer mobile: no optimize surface (assert absence)                         |

---

## 5. Admin API (`API-A-*`)

Base: `/v1/admin` operations optimize family (exact mount per OpenAPI census).

| ID        | P   | Case                                                                                                 |
| --------- | --- | ---------------------------------------------------------------------------------------------------- |
| API-A-001 | P0  | `GET .../optimize/pool` returns merchants/orders/vehicles with sync flags                            |
| API-A-002 | P0  | `GET .../optimize/engines` lists Fleetbase engines (via `_orch.engines()`), never invents PC engines |
| API-A-003 | P0  | `POST .../optimize/run` with default body → `{status:pending, run_id}` **without** waiting on VROOM  |
| API-A-004 | P0  | Run with `shape=merchant` + `merchant_id` filters order set                                          |
| API-A-005 | P0  | Run with `shape=vehicle` + `vehicle_ids` locks vehicles                                              |
| API-A-006 | P0  | `engine=vroom` default; unknown engine handled/rejected per contract                                 |
| API-A-007 | P0  | `GET .../optimize/runs/{id}` 404 → `optimize_run_not_found`                                          |
| API-A-008 | P0  | Status transitions: pending → ready \| error                                                         |
| API-A-009 | P0  | `POST .../optimize/commit` with assignments + `run_id` idempotent                                    |
| API-A-010 | P0  | Commit with `expected_sequence_version` mismatch → 409 Sequence conflict                             |
| API-A-011 | P0  | RBAC: `dispatch_read` for pool/engines/status; `dispatch` for run/commit                             |
| API-A-012 | P1  | Unsynced orders/vehicles → enqueue skips queue (empty/error message, no adapter call)                |
| API-A-013 | P1  | Placeholder Fleetbase ids (`fb-123`) excluded from pool / resolve                                    |
| API-A-014 | P1  | `PREVIEW_ORDER_CAP` enforced; oversized request rejected or truncated per contract                   |
| API-A-015 | P1  | OpenAPI shapes match `OptimizeRunBody` / `OptimizeCommitBody` / admin TS types                       |
| API-A-016 | P2  | Concurrent commits same `run_id` return same applied result                                          |

---

## 6. Driver API (`API-D-*`)

| ID        | P   | Case                                                                          |
| --------- | --- | ----------------------------------------------------------------------------- |
| API-D-001 | P0  | `POST /driver-api/v1/jobs/optimize` enqueues Fleetbase run; no local TSP      |
| API-D-002 | P0  | Requires synced jobs; else clear error                                        |
| API-D-003 | P0  | `GET .../optimize/runs/{run_id}` status polling                               |
| API-D-004 | P0  | `POST .../accept` applies sequence; emits `optimize.applied`                  |
| API-D-005 | P0  | `POST .../undo` → rolled_back / rejected events                               |
| API-D-006 | P0  | Driver A cannot accept Driver B run (IDOR)                                    |
| API-D-007 | P1  | `insert_order_id` midday insert excludes new from prior assignments correctly |
| API-D-008 | P1  | Offline executor `optimize_route` defaults `preview=false` unless flagged     |
| API-D-009 | P1  | Clerk Bearer invalid → 401; suspended driver blocked                          |

---

## 7. Merchant API (`API-M-*`)

| ID        | P   | Case                                                                               |
| --------- | --- | ---------------------------------------------------------------------------------- |
| API-M-001 | P0  | `POST .../route-imports/{job_id}/optimize` → pending + worker enqueue              |
| API-M-002 | P0  | Idempotent re-POST while pending does not double-queue destructively               |
| API-M-003 | P0  | Cross-merchant job_id → 404/403                                                    |
| API-M-004 | P1  | Geocode incomplete stops → optimize blocked or partial with errors                 |
| API-M-005 | P1  | Worker `apply_optimize_job` persists stop order + quote geometry fields            |
| API-M-006 | P2  | Partner `/v1/merchant-api` ingest path can reach same import optimize (if exposed) |

---

## 8. Engine / unit (`ENG-*`)

| ID      | P   | Case                                                                                        |
| ------- | --- | ------------------------------------------------------------------------------------------- |
| ENG-001 | P0  | `OrchestratorOpsService.enqueue_run` writes store + queue; **does not** call adapter        |
| ENG-002 | P0  | `execute_queued_run` calls adapter `run`, writes ready + metrics                            |
| ENG-003 | P0  | `commit` → `commit_orchestrator` → Fleetbase COMMIT_PATH                                    |
| ENG-004 | P0  | `DriverRouteOptimizer` has no local TSP / nearest-neighbor solver                           |
| ENG-005 | P0  | `MerchantRouteImportService.optimize` only enqueues; worker applies                         |
| ENG-007 | P1  | Fuel enrichment `_enrich_fuel_scorecard` attaches liters/cents without mutating assignments |
| ENG-008 | P1  | Intelligence `get_optimize_run` / `get_fuel_delta` read-only                                |
| ENG-009 | P1  | `_enqueue_driver_book_optimize` after assign uses same queue                                |
| ENG-010 | P2  | Circuit breaker on Fleetbase client: open → fail fast; 4xx does not trip                    |

---

## 9. Maps / Valhalla / OSRM / Google (`MAP-*`)

| ID      | P   | Case                                                                                                                                     |
| ------- | --- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| MAP-001 | P0  | Engines call only public Maps APIs (`route`, `matrix_durations`, `optimized_route`, …) — never `_osrm_*` / `_valhalla_*` from `*_engine` |
| MAP-002 | P0  | Valhalla up → primary path; Valhalla down → OSRM fallback                                                                                |
| MAP-003 | P0  | `osrm_allow_public_demo=false` by default; unlabeled `router.project-osrm.org` fails CI                                                  |
| MAP-004 | P0  | Google Places autocomplete works on address entry; **no** Google Distance Matrix in optimize                                             |
| MAP-005 | P1  | `optimized_route_from_valhalla` + polyline precision 6→5 for Google Maps clients                                                         |
| MAP-006 | P1  | Vehicle class costing (box vs auto) via Valhalla costing selector                                                                        |
| MAP-007 | P1  | Matrix durations shape matches assignment scoring consumers                                                                              |
| MAP-008 | P1  | Isochrone / ETA helpers unused by VROOM commit (no accidental coupling)                                                                  |
| MAP-009 | P2  | Live map geometry after optimize uses MapsService polyline                                                                               |
| MAP-010 | P2  | Import `maps.sequence` drop-order keeps pickup first and shortens path                                                                   |

---

## 10. Fleetbase + VROOM (`FB-*`, `VRM-*`)

| ID      | P   | Case                                                                                     |
| ------- | --- | ---------------------------------------------------------------------------------------- |
| FB-001  | P0  | No `import` of VROOM client under `apps/api/**/_engine` (CI / ripwire / census)          |
| FB-002  | P0  | Orchestrator run uses Fleetbase public API (fleetops orchestrator), not PC HTTP to VROOM |
| FB-003  | P0  | Commit assignments normalize via `normalize_commit_result`                               |
| FB-004  | P0  | Web portals never fetch Fleetbase HTTP or SocketCluster                                  |
| FB-005  | P1  | Booking sync must mint real Fleetbase order/vehicle/driver ids before pool eligibility   |
| FB-006  | P1  | Retry queue replays failed sync without duplicate optimize commit                        |
| FB-007  | P1  | Webhook status updates do not wipe sequence applied by optimize                          |
| VRM-001 | P0  | Compose: `VROOM_ROUTER=valhalla`; vroom depends on valhalla                              |
| VRM-002 | P0  | Local VROOM health via Fleetbase engines probe — not direct PC `/solve` productization   |
| VRM-003 | P1  | Greedy engine path still goes through Fleetbase orchestrator                             |
| VRM-004 | P2  | VROOM timeout / empty solution → ready with empty assignments + message                  |

---

## 11. Auth / Clerk / Staff / RBAC (`AUTH-*`)

| ID       | P   | Case                                                                                                    |
| -------- | --- | ------------------------------------------------------------------------------------------------------- |
| AUTH-001 | P0  | Admin optimize uses staff session (`pc_staff_sid` / `Bearer staff_sess_*`), not retired admin Clerk JWT |
| AUTH-002 | P0  | Merchant optimize uses Clerk org context                                                                |
| AUTH-003 | P0  | Driver optimize uses Clerk driver Bearer                                                                |
| AUTH-004 | P0  | Module matrix: missing `dispatch` cannot commit                                                         |
| AUTH-005 | P1  | Dev bypass (`CLERK_DEV_BYPASS`) works locally; disabled in prod-shaped env                              |
| AUTH-006 | P1  | Step-up / security settings do not break ops optimize token refresh                                     |
| AUTH-007 | P2  | SpiceDB Check not cached-allow on dispatch mutate                                                       |

---

## 12. Events / worker (`EVT-*`, `WRK-*`)

| ID      | P   | Case                                                                                   |
| ------- | --- | -------------------------------------------------------------------------------------- |
| EVT-001 | P0  | Enqueue emits `optimize.enqueued`                                                      |
| EVT-002 | P0  | Ready emits `optimize.ready`                                                           |
| EVT-003 | P0  | Commit emits `optimize.applied`                                                        |
| EVT-004 | P0  | Reject / undo emit `optimize.rejected` / `optimize.rolled_back`                        |
| EVT-005 | P1  | Non-default engine still tagged correctly in payload (`DEFAULT_OPTIMIZE_ENGINE=vroom`) |
| EVT-006 | P1  | Catalog aliases `OptimizeEnqueued` ↔ `optimize.enqueued` round-trip                    |
| EVT-007 | P2  | Optional `route.optimized` still coherent with import path                             |
| WRK-001 | P0  | Worker `_optimize_run(run_id)` executes queued run exactly once under concurrency      |
| WRK-002 | P0  | Worker `_optimize_import(job_id)` applies merchant optimize                            |
| WRK-003 | P1  | Worker crash mid-run leaves recoverable pending/error, not silent orphan               |
| WRK-004 | P1  | Redis/EventBus down → visible failure; no fake ready                                   |

---

## 13. Sequence CAS / fuel (`SEQ-*`, `FUEL-*`)

| ID       | P   | Case                                                                          |
| -------- | --- | ----------------------------------------------------------------------------- |
| SEQ-001  | P0  | Accept with stale `expected_sequence_version` → `SequenceConflictError` / 409 |
| SEQ-002  | P0  | Two devices accept same run → one wins, one conflicts                         |
| SEQ-003  | P1  | Deliver stop then reoptimize does not resurrect completed stops               |
| FUEL-001 | P0  | Metrics include fuel scorecard when SystemConfig/FuelConfig present           |
| FUEL-002 | P1  | `fuel_delta` vs pre-plan distance is signed correctly                         |
| FUEL-003 | P2  | Box vs van liters/100km ordering preserved in tests                           |

---

## 14. Notifications / email / FCM (`NOTIF-*`)

| ID        | P   | Case                                                                                            |
| --------- | --- | ----------------------------------------------------------------------------------------------- |
| NOTIF-001 | P1  | On `optimize.applied`, affected drivers receive FCM (or loud ops push policy)                   |
| NOTIF-002 | P1  | Admin notification inbox/realtime receives apply event when subscribed                          |
| NOTIF-003 | P1  | Email path (Mailpit local): if enabled for sequence change, message lands; if disabled, no send |
| NOTIF-004 | P1  | Firebase used for FCM only — not auth                                                           |
| NOTIF-005 | P2  | Push failure does not roll back committed sequence (best-effort notify)                         |
| NOTIF-006 | P2  | Sandbox / `is_sandbox` orders do not spam prod push topics                                      |
| NOTIF-007 | P2  | `PushHealthStrip` reflects token registration after driver optimize accept                      |

---

## 15. Database / models (`DB-*`)

| ID     | P   | Case                                                                                |
| ------ | --- | ----------------------------------------------------------------------------------- |
| DB-001 | P0  | Orders in pool require consumable Fleetbase public id                               |
| DB-002 | P0  | `BulkImportJob` stores optimize_status / stop order / geometry JSON safely          |
| DB-003 | P0  | Driver/Vehicle online + synced flags gate `_synced_fleet`                           |
| DB-004 | P1  | Optimize run store keyed by `run_id`; TTL/expiry behavior documented/tested         |
| DB-005 | P1  | Alembic migrations never drop optimize-related JSON without backfill                |
| DB-006 | P2  | Concurrent worker updates use row/version discipline (no lost update on job config) |

---

## 16. Shopify / ERP / other connections (`INT-*`, `API-S-*`)

| ID        | P   | Case                                                                                  |
| --------- | --- | ------------------------------------------------------------------------------------- |
| API-S-001 | P0  | Shopify carrier rates HMAC valid → rates from pricing + Maps distance (**not** VROOM) |
| API-S-002 | P0  | Invalid HMAC → 401; rate limit `TRAFFIC_SHOPIFY_CARRIER` enforced                     |
| API-S-003 | P1  | Carrier registration URL points at PC API, not Fleetbase                              |
| INT-001   | P1  | Shopify order ingest → merchant booking → (optional) route import optimize enqueue    |
| INT-002   | P1  | Partner API / ERP CSV/JSON import uses same `MerchantRouteImportService` optimize     |
| INT-003   | P2  | Website SEO “route optimization” copy does not imply a public VROOM API               |
| INT-004   | P2  | No SocketCluster subscribe from Shopify app or portals                                |
| INT-005   | P3  | Future ERP (NetSuite/SAP) must reuse import+enqueue — forbid new PC solver            |

---

## 17. Docker / diagnostics / architecture (`DOC-*`, `DIAG-*`, `ARCH-*`)

| ID       | P   | Case                                                                        |
| -------- | --- | --------------------------------------------------------------------------- |
| DOC-001  | P0  | `docker compose` Valhalla digest pin; no `:latest`                          |
| DOC-002  | P0  | OSRM serves `/data/gta-150km.osrm`; prepare scripts document GTA ±150 km    |
| DOC-003  | P0  | VROOM profile starts only with routing profile; config mounted read-only    |
| DOC-004  | P1  | Fleetbase override `ROUTING_ENGINE=valhalla`                                |
| DOC-005  | P1  | API env points Maps to local Valhalla/OSRM, not public demo                 |
| DIAG-001 | P0  | Diagnostics `_probe_vroom` hits orchestrator engines, not a PC VROOM client |
| DIAG-002 | P1  | Integration health surfaces Fleetbase + routing reachability                |
| ARCH-001 | P0  | `scripts/verify_no_ops_spatial_math.py` clean                               |
| ARCH-002 | P0  | OpenAPI census still single public interface per persona                    |
| ARCH-003 | P0  | Thin router: `optimize_*` only `_invoke` + one service call                 |
| ARCH-004 | P0  | No new PorterChain VROOM client under `services/` outside Fleetbase adapter |
| ARCH-005 | P1  | Graphify god-node list still treats Maps + Orchestrator as black boxes      |
| ARCH-006 | P2  | Rejected overlays (`core/blackbox/routing.py`) not reintroduced             |

---

## 18. Free stack only

---

## 19. Suggested automated harness mapping

| Layer                                    | Prefer                                                                                                         |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| **P0 commit / CAS / idempotency / undo** | `test_optimize_commit_p0.py` (**added 2026-09-17**)                                                            |
| Queue / enqueue / no adapter             | `test_optimize_run_queue.py`, `test_step2_optimize_enqueue.py`                                                 |
| Sequence store apply / rollback          | `test_phase5_ops_hardening.py`                                                                                 |
| Driver preview → accept                  | `test_phase_ui_driver_preview.py`                                                                              |
| No local TSP                             | `test_gps_ingest_wave4.py`, `test_remaining_to_live_prove.py`                                                  |
| Import optimize                          | `test_import_route_optimize.py`, `test_route_import_*.py`                                                      |
| Events                                   | `test_phase5c_baseline_events.py`                                                                              |
| Offline                                  | `test_offline_optimize_route.py`                                                                               |
| Fuel                                     | `test_fuel_scorecard.py`                                                                                       |
| Adapter                                  | `services/fleetbase-adapter/tests/test_orchestrator.py`, timeout breaker                                       |
| Maps costing / polyline                  | `services/python/tests/test_valhalla_costing.py`, `test_polyline.py`                                           |
| Shopify rates                            | `test_shopify_carrier_*`                                                                                       |
| Architecture CI                          | `verify_no_ops_spatial_math.py`, `verify_vendor_leaves.py`, OpenAPI census                                     |
| Admin UI                                 | `e2e/optimize.p0.spec.ts` (`UI-OPS-006`, `ADMIN_RUN_LIVE=1`) · Playwright/manual on `/operations` Optimize tab |
| Mobile                                   | Detox/manual JobsScreen optimize + offline queue                                                               |
| **RBAC / IDOR**                          | `test_optimize_rbac_idor.py` (dispatch vs dispatch_read; driver cross-run 404)                                 |

### P0 pytest one-liner (local)

```bash
cd apps/api && source .venv/bin/activate && \
PYTHONPATH=src:../../services/driver-platform:../../services/python:../../shared/python:../../services/pricing-engine \
pytest tests/test_optimize_commit_p0.py tests/test_optimize_rbac_idor.py \
  tests/test_optimize_run_queue.py tests/test_step2_optimize_enqueue.py \
  tests/test_phase5_ops_hardening.py tests/test_phase_ui_driver_preview.py \
  tests/test_offline_optimize_route.py -q
```

### Playwright Optimize smoke

```bash
# terminal A: admin with local bypass
CI=true pnpm dev:admin
# terminal B:
ADMIN_RUN_LIVE=1 pnpm --filter @porterchain/admin test:e2e -- e2e/optimize.p0.spec.ts
```

---

## 20. Things you asked for — coverage map

| You asked                               | Where in this catalog |
| --------------------------------------- | --------------------- |
| Each page / subpage                     | §1.1–1.3 + §2–4       |
| Files / subfiles                        | §1.4–1.5 inventory    |
| API / FastAPI / endpoints               | §5–7                  |
| Microservices / worker                  | §8, §12               |
| Fleetbase / VROOM                       | §10                   |
| Valhalla / OSRM / Google                | §9                    |
| Firebase / push / email / notifications | §14                   |
| Clerk / auth                            | §11                   |
| Models / database                       | §15                   |
| Docker / architecture / handshakes      | §10, §17              |
| Shopify / other ERP                     | §16                   |
| UI / UX                                 | §2.6, §3, §4          |
| Backend engines                         | §8                    |

### Gaps you did not list (added here)

2. **Sequence CAS / multi-device conflict** — §13.
3. **Offline driver optimize queue** — §4 / API-D-008.
4. **Fuel scorecard on plans** — §13.
5. **Public OSRM demo last-resort gate** — MAP-003.
6. **Preview order cap + placeholder fb ids** — API-A-013/014.
7. **Intelligence/copilot read tools** — ENG-008 / A-UI-043.
8. **Spatial-math ban CI** — ARCH-001.
9. **Partner merchant-api / ERP reuse of import** — INT-002.
10. **Diagnostics VROOM probe semantics** — DIAG-001.
11. **Idempotent commit by `run_id`** — API-A-009/016.
12. **Sandbox push isolation** — NOTIF-006.

### Explicit non-goals (do not write cases that encourage)

- Building a PorterChain VROOM/TSP HTTP client.
- Using Google for distance/ETA/matrix/geometry in optimize.
- Rebuilding a Fleetbase dispatch board in admin.
- Calling SocketCluster from any web/mobile app.

---

## 21. P0 checklist (minimum green bar)

| #   | Gate                                                | Automated seed                                                                                      |
| --- | --------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| 1   | Admin Optimize: pool → run → poll ready → commit    | `test_optimize_run_queue` + `test_optimize_commit_p0` (UI still manual/Playwright)                  |
| 2   | Enqueue never blocks on solver                      | `test_optimize_run_queue`, `test_step2_optimize_enqueue`                                            |
| 3   | No local TSP                                        | `test_gps_ingest_wave4`, `verify_no_ops_spatial_math`                                               |
| 4   | Driver accept/undo + sequence CAS                   | `test_phase_ui_driver_preview`, `test_phase5_ops_hardening`, `test_optimize_commit_p0`              |
| 5   | Merchant route-import optimize enqueue              | `test_step2_optimize_enqueue`, `test_import_route_optimize`                                         |
| 6   | Valhalla-first / OSRM fallback / Google places-only | Maps unit + `verify_vendor_leaves` / policy                                                         |
| 7   | VROOM only via Fleetbase                            | `verify_vendor_leaves`, adapter orchestrator tests                                                  |
| 8   | Events enqueued/ready/applied                       | `test_phase5c_baseline_events` (+ accept emit in preview tests)                                     |
| 9   | RBAC/IDOR                                           | `test_optimize_rbac_idor.py` (sales 403; support read-only; driver cross-run 404)                   |
| 10  | Arch guards                                         | `verify_no_ops_spatial_math`, `verify_vendor_leaves`, commit isolation in `test_optimize_commit_p0` |
| UI  | OptimizePanel smoke                                 | `apps/admin/e2e/optimize.p0.spec.ts` (`UI-OPS-006`, `ADMIN_RUN_LIVE=1`)                             |

---

## 22. Recommended next passes

When implementing cases, keep **one sensor hot**:

| If editing…                                            | Sensor                                    |
| ------------------------------------------------------ | ----------------------------------------- |
| Cross-system mash-up / “where does X live”             | Graphify                                  |
| Pydantic `Optimize*` / Maps/Valhalla/OSRM shapes       | CodeGraph                                 |
| Thin routers, adapter, `OptimizePanel`, portal clients | Ripwire `--for` / `--expand` / `--impact` |
