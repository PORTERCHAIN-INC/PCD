# CodeGraph contracts — Quote · Visitor · Optimize (Moment B)

**Status:** living field-level SSOT for P0 pytest assertions.  
**Sensor:** CodeGraph CLI `explore` (2026-09-17) — **not** Graphify / Ripwire this moment.  
**Entry:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Implement pack:** `apps/api/tests/test_hs_wui_mprte_codegraph_p0.py`.

MapsService source was **⚠ changed on disk** vs index — live file re-read: `services/python/porterchain_services/maps/service.py`.

---

## 1. MapsService (HS-09 / HS-10 / W-SPA / MP-RTE-002)

| Symbol                                                                                       | Contract                                                                                               |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| `route_with_source(origin, dest, *, costing, vehicle_class) -> tuple[dict\|None, str\|None]` | Second value ∈ `{None, "valhalla", "osrm"}` — never `"google"`                                         |
| Valhalla path                                                                                | `engine == "valhalla"` + `valhalla_url` → `_valhalla_route`; on miss → `_osrm_route` if `_osrm_base()` |
| `route_distance_meters(points) -> (meters, duration_s, source)`                              | Same source labels                                                                                     |
| `HTTP_TIMEOUT_S`                                                                             | `2.0`                                                                                                  |
| `OSRM_PUBLIC_DEMO_LAST_RESORT`                                                               | Labeled; only if `osrm_allow_public_demo`                                                              |

**Facade:** `porterchain_api.services.routing.resolve_route_distance` → MapsService only.

---

## 2. VisitorSession ORM + VisitorTrackingService (W-VIS / W-API)

**ORM** `booking_models.VisitorSession` (`visitor_sessions`):

| Column                                              | Type notes                          |
| --------------------------------------------------- | ----------------------------------- |
| `id`                                                | `String(64)` PK (client session id) |
| `ip_hash`, `browser`, `utm_*`, `referrer`, `device` | nullable strings                    |
| `location`, `signals`                               | JSON bags                           |
| `touch_count`, `intent_score`                       | int defaults 0                      |
| `quote_generated`                                   | bool                                |
| `last_quote_id`, `customer_id`                      | nullable                            |

**Service** `VisitorTrackingService`:

| Method                                               | Behavior                                                                                                               |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `ensure_session(..., session_id, utm_*, signals, …)` | upsert; bump `touch_count`; recompute `intent_score`; emit `VISITOR_SESSION_STARTED` on create                         |
| `record_quote(db, session_id, quote_id)`             | `quote_generated=True`, `last_quote_id`, signal `intent=quote`                                                         |
| `merge_to_customer(db, session_id, customer_id)`     | set FK; emit `SESSION_MERGED` even if session missing                                                                  |
| `signals_from_tracking(tracking)`                    | keys: landing_page, from_page, locale, source_page, page_view_count, paths, intent, guide_stage, utm_term, utm_content |

**Pydantic** `schemas_booking.VisitorTrackingInput` — same signal keys + browser/utm/referrer/device/location.  
**Pydantic** `CreateQuoteRequest` — `anonymous_session_id`, `visitor_session_id`, `tracking: VisitorTrackingInput | None`.  
**Pydantic** `QuoteResponse` — `quote_id`, `amount_cents`, `pricing_breakdown: list[PricingLineItem]`, `distance_km` (not `distance_source` on response — source lives on Maps facade / internal).

**Customer link:** `Customer.visitor_session_id`; `Quote.visitor_session_id` + `anonymous_session_id`.

---

## 3. Optimize / VROOM (HS-13 / MP-RTE-002b / VR enqueue)

**Pydantic** `schemas_admin.OptimizeRunBody`:

| Field                                                   | Default                                     |
| ------------------------------------------------------- | ------------------------------------------- |
| `mode`                                                  | `"allocate"`                                |
| `engine`                                                | `"vroom"`                                   |
| `shape`                                                 | `"fleet"` (`merchant` \| `vehicle` allowed) |
| `order_ids`, `merchant_id`, `vehicle_ids`, `driver_ids` | optional                                    |

**Service** `OrchestratorOpsService.enqueue_run`:

- Resolves Fleetbase public ids; empty → `{ok:false, error: no_synced_orders|…}` — **no** adapter call.
- On success writes pending run + `enqueue_optimize_job(run_id)` — **no** inline Fleetbase HTTP.
- Default `engine="vroom"` (Fleetbase orchestrator engine id, not a PC client).

**Merchant** `MerchantRouteImportService.optimize`:

- Requires unconfirmed job; geocode not `failed`/`pending`.
- Sets `job_config.optimize_status="pending"`, `optimized=False`.
- `_enqueue_optimize` → `enqueue_routing_job({"action": "optimize_import", "job_id"})`.
- **Does not** call MapsService TSP / VROOM HTTP.

**Commit** `OptimizeCommitBody`: `assignments`, optional `run_id` (idempotent), `pc_driver_id`, `expected_sequence_version`.

---

## 4. Blast radius (CodeGraph)

| Hub                                  | Dependents to keep green                                                  |
| ------------------------------------ | ------------------------------------------------------------------------- |
| `MapsService.route_with_source`      | `resolve_route_distance`, public tracking, live map, scoring, driver nav  |
| `VisitorTrackingService`             | `quote_service`, `public_guide`, `customer_service`, visitor_intelligence |
| `OrchestratorOpsService.enqueue_run` | OptimizePanel, driver `JobsService.optimize_route`, worker dispatch       |

Seeds already green: `test_optimize_run_queue.py`, `test_step2_optimize_enqueue.py`, `merchant_p0/test_p0_handshakes.py`, `test_wave4_batch_c.py`, `test_merchant_matrix_p0_arch.py`.

---

## 5. Moment C (done) — Ripwire

See [RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md](RIPWIRE_QUOTE_VISITOR_OPTIMIZE.md). Website Playwright scaffolds live under `website/e2e/`.
