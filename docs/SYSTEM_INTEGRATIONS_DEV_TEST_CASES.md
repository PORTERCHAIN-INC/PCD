# System integrations — development test cases

> **Cutover (2026-10):** Fleetbase adapter, bond handshake, and VROOM client are **removed**.
> Dispatch is PorterChain OR-Tools + Valhalla. Historical Fleetbase rows / seeds below are
> retired; SSOT is [ARCHITECTURE.md](../ARCHITECTURE.md).

**Status:** living catalog for local/CI development (not prod Doppler validation).  
**Mapped:** 2026-09-17 via Graphify (`query` / `god-nodes` / adapter subgraph) + `ARCHITECTURE.md` + `diagnostics_catalog.TEST_CATALOG`.  
**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md). Heatmap sibling: [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md).  
**Companion:** [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md) (retail customer + Admin Customers).  
**Maps / Firebase / Push deep slice (Graphify → CodeGraph → Ripwire):** [MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md](MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md).  
**Skips SSOT:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) — do not invent cases that reopen held policy.

**Sensor note:** This file’s first pass was **Graphify only**. When implementing cases, use CodeGraph then Ripwire (never all three in one session):

| Moment | Tool                                       | Use for                                                                                                    |
| ------ | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------- |
| B      | CodeGraph `explore`                        | Pydantic/ORM: `FleetbaseSyncJob`, `Order`, MapsService, Valhalla costing, webhook / FCM payloads           |
| C      | Ripwire `--for` / `--callers` / `--impact` | Thin routers, `fleetbase-adapter`, Clerk/Stripe/Shopify, portal `lib/*`, `web-push`, mobile `handshake.ts` |

**Existing coverage seed (expand; do not duplicate):**

| Area                    | Seed tests / probes                                                                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Fleetbase adapter       | `services/fleetbase-adapter/tests/*`, `apps/api/tests/test_fleetbase_adapter_contract.py`                                                                 |
| Sync / retry / webhooks | `test_fleetbase_webhook_retry.py`, `test_retry_queue_phase1.py`, `test_fleetbase_sync_health.py`, `test_status_translator.py`, `test_gps_ingest_wave*.py` |
| Shopify handshakes      | `test_shopify_carrier_pricing_handshake.py`, `test_shopify_*.py`                                                                                          |
| Clerk / identity        | `test_clerk_registry.py`, `test_auth_*.py`, `test_unified_identity_phase*.py`                                                                             |
| Stripe                  | `test_stripe_*.py`                                                                                                                                        |
| Notifications / FCM     | `test_notification_*.py`, `test_zeptomail_https_delivery.py`                                                                                              |
| ERP                     | `test_netsuite_zapier.py`, `test_merchant_integrations.py`                                                                                                |
| Spatial                 | `services/python/tests/test_valhalla_costing.py`, `test_routing.py`, `test_offline_optimize_route.py`, `test_orchestrator_ops.py`                         |
| Live probes             | Admin `/system?tab=tests` (+ aliases `/system-tests`, `/system-health` → `/system`) + `diagnostics_*` (`TEST_CATALOG` ids)                                |
| Architecture gates      | `pnpm validate:architecture`, `validate:golden-rules`, `validate:d2`, `validate:p0`, `validate:e2e`                                                       |

**Charter gate:** Prefer cases that protect **network execution integrity** (Fleetbase handshakes), **money**, **identity**, **capacity utilization**, and **fail-closed degrade**. Skip Phase 2 / Future Fleetbase modules unless flagged on.

---

## 0. ID scheme & layers

| Prefix     | Layer                                                                                                                                                            |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `FB-HS-*`  | Fleetbase connection / auth / circuit / handshake                                                                                                                |
| `FB-AD-*`  | Adapter modules (`client`, `orders`, `drivers`, `vehicles`, `dispatch`, `pod`, `tracking`, `orchestrator`, `zones`, `routes`, `manifests`, `webhooks`, `events`) |
| `FB-ENG-*` | `fleetbase_engine` (BookingSync, WebhookProcessor, RetryQueue, StatusTranslator, TrackingFacade, IntegrationBridge)                                              |
| `FB-UI-*`  | Admin / merchant / driver surfaces that **must not** call Fleetbase HTTP                                                                                         |
| `SPA-*`    | Valhalla / OSRM / MapsService / Google Places+tiles only                                                                                                         |
| `VR-*`     | VROOM via Fleetbase orchestrator only (never PC HTTP client)                                                                                                     |
| `AUTH-*`   | Clerk / Staff IdP / SpiceDB / RBAC / IDOR                                                                                                                        |
| `PAY-*`    | Stripe Checkout / COD Connect / webhooks                                                                                                                         |
| `NOTIF-*`  | FCM / email / Mailpit / ZeptoMail / notification_engine                                                                                                          |
| `SH-*`     | Shopify OAuth / CarrierService / webhooks / Quote≡Book                                                                                                           |
| `ERP-*`    | NetSuite / Zapier / `ErpFulfillmentAdapter` / merchant API keys                                                                                                  |
| `API-*`    | FastAPI routers / OpenAPI census / persona prefixes                                                                                                              |
| `WRK-*`    | Worker processors / EventBus / queue drain                                                                                                                       |
| `DB-*`     | Postgres / Alembic / FleetbaseSyncJob / models                                                                                                                   |
| `DOC-*`    | Docker / compose pins / ports / Valkey / Mailpit                                                                                                                 |
| `ARCH-*`   | Architecture contracts / D2 / vendor leaves / no SocketCluster in web                                                                                            |
| `A-UI-*`   | Admin portal pages / subpages                                                                                                                                    |
| `M-UI-*`   | Merchant portal pages / subpages                                                                                                                                 |
| `D-UI-*`   | Driver web BFF + mobile handshake                                                                                                                                |
| `DIAG-*`   | Diagnostics catalog probes (`TEST_CATALOG` ids)                                                                                                                  |
| `E2E-*`    | Local loop / nightly e2e / portal smoke                                                                                                                          |

**Priority:** P0 = ship-blocker handshake · P1 = money/trust/execution · P2 = regression/polish · P3 = parked / intentional-skip verification only.

Each case: **ID · P · Precondition → Steps → Expected · Tags · Seed**.

---

## 1. Architecture trunk (must stay true)

| ID       | P   | Case                                                                                | Expected                                                                                                          | Seed                                                          |
| -------- | --- | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| ARCH-001 | P0  | Portals never import Fleetbase HTTP or SocketCluster SDK                            | `validate:architecture` + vendor-leaves CI fail on `:8000` / `fleetbase` / SC under portals & `apps/mobile-*/src` | `verify_vendor_leaves.py`, `layered_architecture` probe       |
| ARCH-002 | P0  | Request path: portal → `:8001` → thin router → `*_engine` → adapter                 | No new inline `BaseModel` in routers; no engine→Fleetbase HTTP bypassing adapter                                  | `verify_router_audit.py`, `verify_architecture_boundaries.py` |
| ARCH-003 | P0  | Spatial priority Valhalla → OSRM → (labeled public OSRM last resort off by default) | Google never used for distance/ETA/matrix/geometry for pricing/dispatch                                           | `verify_no_ops_spatial_math.py`, SPA cases                    |
| ARCH-004 | P0  | VROOM only behind Fleetbase orchestrator                                            | No `vroom` HTTP client under `*_engine`                                                                           | `diagnostics_fleetbase_probes._probe_vroom`, intentional skip |
| ARCH-005 | P0  | OpenAPI census: every business path tagged to a persona                             | New untagged path fails CI                                                                                        | `scripts/openapi_census.py` (639 ops)                         |
| ARCH-006 | P1  | Wholesale route templates stay                                                      | `/v1/admin/route-templates` remains on the admin API. The August 2026 “cut endpoints” ban is retired.             | `test_removed_ops_endpoints.py`                               |
| ARCH-007 | P0  | Project mode boot-time only                                                         | `POST …/project-mode` → `403 project_mode_immutable`                                                              | intentional skip + `project_mode.py`                          |
| ARCH-008 | P1  | God nodes stay coherent                                                             | Settings / Order / MerchantContext remain hubs; no new mash-up engines                                            | Graphify `god-nodes` after folder-graph change                |

---

## 2. Fleetbase connection & handshakes

### 2.1 Config / client / circuit

| ID        | P   | Case                                                       | Expected                                                                                                                                              | Seed                                                           |
| --------- | --- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| FB-HS-001 | P0  | `FLEETBASE_API_KEY` + base URL configured in local compose | Adapter constructs `FleetbaseClient`; probe `fleetbase` / `fleetbase_adapter` green when live                                                         | `_probe_fleetbase*`                                            |
| FB-HS-002 | P0  | Missing key → `FleetbaseNotConfiguredError`                | Fail closed; sync jobs enqueue retry, UI shows degrade — no silent success                                                                            | adapter `exceptions.py`                                        |
| FB-HS-003 | P0  | Timeout / 5xx opens circuit breaker                        | `FleetbaseCircuitOpenError`; subsequent calls short-circuit until cool-down                                                                           | `test_client_timeout_breaker.py`                               |
| FB-HS-004 | P0  | Retry policy respects idempotent methods                   | Safe retries on GET; mutating ops use RetryQueue LWW / job id                                                                                         | `retry.py`, `test_retry_queue_phase1.py`                       |
| FB-HS-005 | P1  | Adapter contract version stable                            | `adapter_module_version()` / contract tests pin public surface                                                                                        | `test_contract.py`, `test_fleetbase_adapter_contract.py`       |
| FB-HS-006 | P1  | Console probe vs API probe diverge correctly               | Console SSO link optional; API key health independent                                                                                                 | `_probe_fleetbase_console`                                     |
| FB-HS-007 | P0  | Reverse dispatcher key                                     | `PORTERCHAIN_DISPATCHER_API_KEY` accepted only on documented reverse routes                                                                           | FLEETBASE_MODULES Auth                                         |
| FB-HS-008 | P1  | Image pin matches override                                 | Running core-api/fleetops digests match `fleetbase.porterchain.override.yml`                                                                          | DOC cases                                                      |
| FB-HS-009 | P0  | Permanent bond handshake                                   | `verify_bond` / `run_boot_handshake` → authenticated `GET /v1/orders`; readiness `fleetbase_bond=ok`; live adapter probe uses bond not bare host ping | `docs/FLEETBASE_PERMANENT_BOND.md`, `fleetbase_engine/bond.py` |
| FB-HS-010 | P0  | Local bond repair                                          | `pnpm fleetbase:bond` ensures company+key, `OrderConfig` transport, heals missing tables, POST/GET smoke                                              | `repair_fleetbase_local.py`                                    |
| FB-HS-011 | P0  | Entity destination FK safety                               | UUID-shaped PC stop ids must **not** set `destination_uuid` (stock places FK); use `meta.destination_import_id`                                       | `mappers.py`, `test_mappers.py`                                |
| FB-HS-012 | P0  | Seed hygiene vs G2                                         | Unlinked seed purged (`pnpm fleetbase:purge-seed`); do not mass-backfill dummies; G2 ≥98% on remaining eligible                                       | `purge_unlinked_seed_orders.py`, `validate:p0:fast`            |

### 2.2 Booking sync handshake (PC → Fleetbase)

| ID         | P   | Case                                                | Expected                                                                     | Seed                                                |
| ---------- | --- | --------------------------------------------------- | ---------------------------------------------------------------------------- | --------------------------------------------------- |
| FB-ENG-001 | P0  | Confirmed booking → `BookingSyncService.push_order` | Fleetbase order created; `porterchain_order_id` in meta; PC stores public id | `booking_sync_service.py`                           |
| FB-ENG-002 | P0  | Push failure → `RetryQueue.enqueue`                 | `FleetbaseSyncJob` row; worker drains; SLO health visible                    | `test_fleetbase_sync_health.py`                     |
| FB-ENG-003 | P0  | Driver assignment push                              | `push_driver_assignment` mirrors CT assign                                   | same                                                |
| FB-ENG-004 | P0  | Status push `_push_status`                          | PC state → Fleetbase activity without double-fire                            | `test_status_translator.py`                         |
| FB-ENG-005 | P1  | Drain kinds exhaustive                              | New sync kinds cannot be “unhandled”                                         | `test_retry_queue_phase1.py::test_new_drain_kinds…` |
| FB-ENG-006 | P1  | LWW on integrity conflict                           | Newer `last_known` wins / re-enqueue                                         | `test_gps_ingest_wave01.py`                         |
| FB-ENG-007 | P1  | Replay script                                       | `scripts/replay_fleetbase_sync.py` reprocesses stuck jobs safely             | script + sync health                                |
| FB-ENG-008 | P0  | Sandbox vs live isolation                           | Sandbox orders never leak into live Fleetbase company                        | phase5c / optimize contracts                        |

### 2.3 Webhook handshake (Fleetbase → PC)

| ID         | P   | Case                                 | Expected                                                                          | Seed                                  |
| ---------- | --- | ------------------------------------ | --------------------------------------------------------------------------------- | ------------------------------------- |
| FB-ENG-010 | P0  | Signed webhook `/webhooks/fleetbase` | Invalid signature rejected; valid → `WebhookProcessor.process`                    | `test_fleetbase_webhook_retry.py`     |
| FB-ENG-011 | P0  | Status update idempotent             | Duplicate delivery does not regress order state                                   | same                                  |
| FB-ENG-012 | P0  | Replay reprocesses update            | Explicit replay path works                                                        | `test_webhook_replay_reprocesses…`    |
| FB-ENG-013 | P1  | StatusTranslator covers lifecycle    | Fleetbase activities map to `OrderState` without inventing states                 | `test_status_translator.py`           |
| FB-ENG-014 | P1  | Tracking facade                      | Public track uses PC snapshot fed by Fleetbase positions poll — not SC in browser | `TrackingFacade`, intentional skip SC |
| FB-ENG-015 | P1  | Audit logger                         | Sync/webhook mutations leave audit trail                                          | `audit_logger.py`                     |

### 2.4 Adapter module matrix (each package)

For each module under `services/fleetbase-adapter/porterchain_fleetbase_adapter/`:

| Module                | Case IDs              | Must assert                                                        |
| --------------------- | --------------------- | ------------------------------------------------------------------ |
| `client`              | FB-AD-010..015        | Auth header, timeout, patch/get, error mapping                     |
| `auth`                | FB-AD-020             | Credential shape; no Clerk leakage into Fleetbase                  |
| `orders`              | FB-AD-030..039        | Create/update/dispatch/cancel; meta `porterchain_order_id`         |
| `drivers`             | FB-AD-040..049        | `sync_driver`, online read, track ingest path via adapter          |
| `vehicles`            | FB-AD-050..055        | Sync capacity → `payload_capacity*`                                |
| `dispatch`            | FB-AD-060..069        | Manual dispatch / assign; never rebuild board in PC                |
| `orchestrator`        | FB-AD-070..079 + VR-* | `optimize_routes` + `engine=vroom`; driver-scoped; commit→manifest |
| `manifests`           | FB-AD-080..085        | Commit creates stops; CAS version                                  | `test_manifests.py`                |
| `pod`                 | FB-AD-090..095        | Signature/photo/QR capture proxied; storage SoT Fleetbase          | `test_d3_dispatch_pod_contract.py` |
| `tracking`            | FB-AD-100..108        | Positions poll; playback                                           | `test_tracking_playback.py`        |
| `routes` / `zones`    | FB-AD-110..119        | Zone filter for CT; no Google matrix                               |
| `webhooks` / `events` | FB-AD-120..129        | Lifecycle translator                                               | `FleetbaseLifecycleTranslator`     |
| `mappers`             | FB-AD-130             | Bidirectional field map golden fixtures                            | `test_mappers.py`                  |
| `integration`         | FB-AD-140             | Facade wires all modules; single entry from API                    | `integration.py`                   |

**Golden path (P0):** Quote → Book → pay/net → `DISPATCH_READY` → push_order → assign → VROOM optimize (Fleetbase) → driver accept → POD → webhook complete → invoice/AR.

---

## 3. Spatial stack (Valhalla / OSRM / Google / VROOM)

| ID      | P   | Case                                            | Expected                                                  | Seed                              |
| ------- | --- | ----------------------------------------------- | --------------------------------------------------------- | --------------------------------- |
| SPA-001 | P0  | MapsService Valhalla-first route                | Returns geometry/distance; source=`valhalla`              | maps `service.py`                 |
| SPA-002 | P0  | Valhalla down → OSRM local `:5000`              | Fallback labeled; pricing still works                     | `_probe_osrm`, `_probe_valhalla`  |
| SPA-003 | P0  | Public OSRM demo default off                    | `osrm_allow_public_demo=false`; CI fails unlabeled public | intentional skip                  |
| SPA-004 | P0  | Engines call only public MapsService APIs       | No `_osrm_*` / `_valhalla_*` from engines                 | architecture gate                 |
| SPA-005 | P1  | Costing by vehicle class                        | Box vs auto costing selector                              | `test_valhalla_costing.py`        |
| SPA-006 | P1  | Matrix for interleaved PUDO                     | Duration matrix among unlocked legs                       | phase4 tests                      |
| SPA-007 | P0  | Google Places autocomplete only                 | Quote UX uses Places; never Distance Matrix               | Google probe + ARCH-003           |
| SPA-008 | P0  | Google tiles on live track maps                 | Tiles OK; ETA from Valhalla/OSRM/Fleetbase                | `validate:tracking-maps`          |
| SPA-009 | P1  | GTA ±150 km tile                                | Out-of-tile quote tagged `in_tile=false` / coverage gap   | FSA / service-area tests          |
| SPA-010 | P1  | Isochrone / ETA helpers                         | Used for CT heuristics only where documented              | MapsService                       |
| VR-001  | P0  | Optimize run enqueued to Fleetbase orchestrator | `engine=vroom`; no PC solver import                       | `test_orchestrator.py`, ops tests |
| VR-002  | P0  | Driver-scoped optimize                          | Cannot pass other drivers’ order_ids                      | phase5c contract                  |
| VR-003  | P1  | Commit idempotent by `run_id`                   | Double commit safe                                        | phase5                            |
| VR-004  | P1  | Sequence CAS 409                                | Admin/driver race handled                                 | phase5                            |
| VR-005  | P2  | cuOpt shadow only                               | Shadow metrics; never replaces VROOM                      | `test_cuopt_shadow.py`            |
| VR-006  | P3  | OrderConfig HOS → VROOM                         | **Assert still NOT implemented** (intentional skip)       | PCD_INTENTIONAL_SKIPS             |

---

## 4. Identity (Clerk / Staff IdP / SpiceDB)

| ID       | P   | Case                                                           | Expected                                                             | Seed                            |
| -------- | --- | -------------------------------------------------------------- | -------------------------------------------------------------------- | ------------------------------- |
| AUTH-001 | P0  | Per-portal Clerk triad via `env/clerk.env` + `pnpm clerk:sync` | No `ADMIN_CLERK_*` ad-hoc names                                      | `test_clerk_registry.py`        |
| AUTH-002 | P0  | Local bypass dual-gated                                        | `CLERK_DEV_BYPASS` only when project mode development                | project_mode + auth tests       |
| AUTH-003 | P0  | Merchant/driver/customer Bearer Clerk                          | Wrong portal secret rejected                                         | auth cutover tests              |
| AUTH-004 | P0  | Admin staff session cookie → API Bearer                        | `pc_staff_sid` / `staff_sess_*`; Clerk JWT retired for admin browser | staff-session                   |
| AUTH-005 | P0  | SpiceDB Check no cached allows                                 | Deny by default on missing tuple                                     | `test_spicedb_authz.py`         |
| AUTH-006 | P0  | IDOR across merchants                                          | Cross-tenant 404/403                                                 | `test_idor.py`, `test_tenant_*` |
| AUTH-007 | P1  | User sync / ensure user                                        | Clerk webhook → PorterchainUser                                      | user_sync / ensure_user         |
| AUTH-008 | P1  | Invitation + activate-staff                                    | Staff activation path                                                | activate-staff page             |
| AUTH-009 | P1  | Hybrid RBAC modules                                            | `require_module` matrix                                              | `test_hybrid_rbac.py`           |
| AUTH-010 | P0  | Firebase Auth not used                                         | FCM-only identity leave                                              | intentional skip                |
| AUTH-011 | P1  | Step-up for sensitive admin                                    | Security page / staff-step-up                                        | account/security                |

---

## 5. Money (Stripe)

| ID      | P   | Case                                                     | Expected                                | Seed                                 |
| ------- | --- | -------------------------------------------------------- | --------------------------------------- | ------------------------------------ |
| PAY-001 | P0  | Checkout retail prepaid                                  | Session URL + webhook settle idempotent | `test_stripe_webhook_idempotency.py` |
| PAY-002 | P0  | Only `porterchain_services/stripe/sdk.py` imports stripe | Allowlist exact                         | architecture                         |
| PAY-003 | P1  | COD Connect + Payment Link additive                      | Does not break Checkout                 | `test_stripe_cod_phase46.py`         |
| PAY-004 | P1  | Merchant AR pay / pay-all server-locked amounts          | Body cents ignored                      | Shopify billing wave                 |
| PAY-005 | P1  | Stripe mock gated                                        | Mock only in development mode           | project_mode                         |
| PAY-006 | P0  | Webhook signature fail closed                            | Bad sig → 4xx, no ledger write          | stripe webhook tests                 |

---

## 6. Notifications (FCM / email / Mailpit)

| ID        | P   | Case                                                        | Expected                                   | Seed                                |
| --------- | --- | ----------------------------------------------------------- | ------------------------------------------ | ----------------------------------- |
| NOTIF-001 | P0  | FCM config probe                                            | `firebase` catalog green when keys present | `_probe_firebase`                   |
| NOTIF-002 | P0  | Device register rejects Expo / fake `web-*`                 | FCM-only                                   | intentional skip + DeviceService    |
| NOTIF-003 | P0  | Staff risk events → loud push                               | Routine parcel milestones stay in_app      | notification phase + loud push docs |
| NOTIF-004 | P1  | Zero device → email failsafe                                | Mailpit locally                            | zeptomail / delivery tests          |
| NOTIF-005 | P0  | Admin SW + foreground onMessage                             | `firebase-messaging-sw.js` registers       | admin web-push                      |
| NOTIF-006 | P1  | Driver channels `ops_critical` / `assignments` / `tracking` | Correct Android channel_id                 | phase tests                         |
| NOTIF-007 | P0  | Mailpit local SMTP                                          | `_probe_mailpit` + message appears         | diagnostics                         |
| NOTIF-008 | P1  | ZeptoMail HTTPS prod path                                   | TLS delivery                               | `test_zeptomail_https_delivery.py`  |
| NOTIF-009 | P0  | No second mail/FCM engine                                   | Single `notification_engine`               | intentional skip                    |
| NOTIF-010 | P1  | Role matrix                                                 | Who receives what                          | `test_notification_role_matrix.py`  |
| NOTIF-011 | P1  | Realtime admin WS notifications                             | Not SocketCluster                          | `test_notification_realtime.py`     |
| NOTIF-012 | P2  | Push health strip on Control Tower                          | Degrade visible                            | PushHealthStrip                     |

---

## 7. Shopify + ERP + partner API

| ID      | P   | Case                                     | Expected                                          | Seed                                        |
| ------- | --- | ---------------------------------------- | ------------------------------------------------- | ------------------------------------------- |
| SH-001  | P0  | CarrierService HMAC → PricingEngine      | Quote≡Book cents                                  | `test_shopify_carrier_pricing_handshake.py` |
| SH-002  | P0  | `shopify_rate_quotes` + quote_id on book | Idempotent                                        | shopify ingest/phase4                       |
| SH-003  | P0  | OAuth install / email hijack blocked     | Fail closed                                       | shopify security tests                      |
| SH-004  | P1  | Rate limits on carrier + webhooks        | 429 under abuse                                   | same                                        |
| SH-005  | P1  | Merchant Shopify page                    | Install/status; no Admin mint                     | M-UI shopify                                |
| SH-006  | P3  | App Store listing / filled `app.toml`    | **Assert still stub**                             | intentional skip                            |
| ERP-001 | P1  | NetSuite adapter contract                | Connection payload + fulfillment map              | `test_netsuite_zapier.py`                   |
| ERP-002 | P1  | Zapier catalog entries                   | Documented triggers/actions only                  | `zapier_catalog.py`                         |
| ERP-003 | P0  | `ErpFulfillmentAdapter` versioned        | Base adapter module version                       | `base_adapter.py`                           |
| ERP-004 | P0  | Merchant API keys                        | Merchant creates; admin revoke/disable only       | `test_merchant_integrations.py`             |
| ERP-005 | P0  | Partner API idempotency                  | `/v1/merchant-api` key + Idempotency-Key          | `test_merchant_api_idempotency.py`          |
| ERP-006 | P1  | Webhook delivery health                  | Outbound merchant webhooks                        | `test_webhook_delivery_health.py`           |
| ERP-007 | P2  | WooCommerce / QuickBooks                 | If absent: document as not-in-repo; do not invent | gap note below                              |

---

## 8. FastAPI / worker / database / docker

### 8.1 API & worker

| ID      | P   | Case                              | Expected                                                    | Seed                              |
| ------- | --- | --------------------------------- | ----------------------------------------------------------- | --------------------------------- |
| API-001 | P0  | `/health` and `/health/ready`     | Ready includes DB + critical deps                           | `test_health.py`, readiness probe |
| API-002 | P0  | Persona prefixes auth             | Staff / merchant / merchant-api / driver-api / public track | ARCH leaf census                  |
| API-003 | P1  | Rate limit middleware             | Gateway abuse limited                                       | `test_rate_limit_middleware.py`   |
| API-004 | P1  | Error envelope stable             | Clients parse `code` / `message`                            | `test_error_envelope.py`          |
| API-005 | P0  | OpenAPI snapshot parity           | `docs/api/openapi.json` matches live                        | `verify_api_readme_openapi.py`    |
| WRK-001 | P0  | Dispatch processor                | Consumes EventBus → Fleetbase sync                          | `test_dispatch_processor.py`      |
| WRK-002 | P0  | Notifications processor           | Drain notification queue                                    | `test_notifications_processor.py` |
| WRK-003 | P0  | Billing processor                 | Ledger jobs                                                 | `test_billing_processor.py`       |
| WRK-004 | P0  | Webhooks processor                | Outbound                                                    | `test_webhooks_processor.py`      |
| WRK-005 | P1  | Event bus smoke                   | Publish + consume                                           | `_probe_event_bus`                |
| WRK-006 | P1  | Queue names frozen                | No silent rename                                            | `test_queue_names.py`             |
| WRK-007 | P1  | Optimize run queue apply_on_ready | Sequence apply worker path                                  | `test_optimize_run_queue.py`      |

### 8.2 Database

| ID     | P   | Case                           | Expected                       | Seed                        |
| ------ | --- | ------------------------------ | ------------------------------ | --------------------------- |
| DB-001 | P0  | Postgres 18 smoke              | Connect + simple query         | `test_postgres_smoke.py`    |
| DB-002 | P0  | Alembic heads apply clean      | Fresh migrate up               | CI migrate                  |
| DB-003 | P0  | `FleetbaseSyncJob` constraints | Unique / LWW integrity         | retry queue tests           |
| DB-004 | P1  | ORM ownership                  | Writes only from owning engine | `verify_model_ownership.py` |
| DB-005 | P1  | Integrity FKs                  | Orphan prevention              | `test_integrity_waves.py`   |
| DB-006 | P1  | Row locks on contention        | No lost updates on status      | `test_row_locks.py`         |

### 8.3 Docker / infra

| ID      | P   | Case                        | Expected                                                                                                                         | Seed               |
| ------- | --- | --------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ------------------ |
| DOC-001 | P0  | No `:latest` images         | Exact tags/digests in compose                                                                                                    | dependency-freeze  |
| DOC-002 | P0  | Ports map                   | API 8001, Valhalla 8002, OSRM 5000, Fleetbase 8000, admin 3002, merchant 3001, website 3000, driver 3003, customer 3004, Mailpit | ARCHITECTURE       |
| DOC-003 | P0  | Fleetbase Valkey 8 override | Not upstream redis:4                                                                                                             | fleetbase override |
| DOC-004 | P0  | Mailpit not Mailhog         | Local email UI                                                                                                                   | `_probe_mailpit`   |
| DOC-005 | P1  | Valhalla digest pin         | `valhalla-scripted@sha256:…`                                                                                                     | compose            |
| DOC-006 | P1  | GTA tile scripts idempotent | prepare-valhalla/osrm scripts documented                                                                                         | infra README       |
| DOC-007 | P1  | Redis 8.8 PC cache          | Separate from Fleetbase Valkey                                                                                                   | redis health tests |
| DOC-008 | P2  | Doppler prod secrets shape  | Examples match `api.env.example` keys                                                                                            | env examples       |

---

## 9. Admin portal — page / subpage matrix

**Rule:** every list/detail route loads with staff session; no Fleetbase `:8000` fetch from browser; degrade banners when probes red.

| Route                                                                                                         | Case IDs      | Must cover                                                                                                    |
| ------------------------------------------------------------------------------------------------------------- | ------------- | ------------------------------------------------------------------------------------------------------------- |
| `/sign-in`                                                                                                    | A-UI-001      | Staff IdP; bypass only local+flag                                                                             |
| `/activate-staff`                                                                                             | A-UI-002      | Invitation redeem                                                                                             |
| `/dashboard`                                                                                                  | A-UI-010      | KPIs; trends shape `{labels,orders,revenue_cents}`                                                            |
| `/operations`                                                                                                 | A-UI-020..029 | Control Tower, OptimizePanel, PushHealthStrip, DispatcherCopilot — wrap Fleetbase, no rebuild board           |
| `/orders`, `/orders/[id]`                                                                                     | A-UI-030..039 | Lifecycle, OrderAssist, Fleetbase link only                                                                   |
| `/merchants`, `/merchants/[id]`                                                                               | A-UI-040..059 | Overview/Billing/Pricing/Locations/StandingOrders — revoke keys, never mint Shopify                           |
| `/drivers`, `/drivers/[id]`                                                                                   | A-UI-060..079 | Compliance badges; sync_driver; documents                                                                     |
| `/customers`, `/customers/[id]`                                                                               | A-UI-080      | See customer persona catalog                                                                                  |
| `/leads`, `/leads/[id]`, `/pipeline`, `/calendar`                                                             | A-UI-090..099 | CRM ingest bus; no Phase3 AI SKU                                                                              |
| `/booking-drafts`, `/[id]`                                                                                    | A-UI-100      | Draft→order handoff                                                                                           |
| `/finance`, `/finance/invoices/[id]`                                                                          | A-UI-110..119 | AR SSOT; pay recording                                                                                        |
| `/pricing`                                                                                                    | A-UI-120      | FSA / simulate; Valhalla distance                                                                             |
| `/notifications`                                                                                              | A-UI-130      | Inbox + FCM register                                                                                          |
| `/claims`, `/claims/[id]`                                                                                     | A-UI-140      | Claims workflow                                                                                               |
| `/support`, `/support/[id]`                                                                                   | A-UI-150      | Tickets                                                                                                       |
| `/inbox`                                                                                                      | A-UI-160      | Staff inbox                                                                                                   |
| `/blog`, `/blog/new`, `/blog/[id]`                                                                            | A-UI-170      | CMS                                                                                                           |
| `/settings`                                                                                                   | A-UI-180..199 | Panels: Coverage, Integrations, LeadIngest, EnvOwned, Users, FSA, Import/Restore — **project mode read-only** |
| `/system` (Health / Tests / AI tabs); aliases `/system-health`→`/system`, `/system-tests`→`/system?tab=tests` | A-UI-200..220 | Run **every** `TEST_CATALOG` id live+config; chaos optional                                                   |
| `/account/security`                                                                                           | A-UI-230      | Step-up / passkey                                                                                             |

**DIAG matrix (map 1:1 to Admin System Tests):**  
`clerk`, `stripe`, `firebase`, `google_maps`, `osrm`, `valhalla`, `vroom`, `fleetbase`, `fleetbase_adapter`, `fleetbase_console`, `email_smtp`, `mailpit`, `event_bus`, `websockets`, `redis`, `postgresql`, `readiness_probe`, `metrics_endpoint`, `worker_queue`, `notification_engine`, `pricing_engine`, `billing_engine`, `orders_engine`, `crm_engine`, `finance_engine`, `claims_engine`, `support_engine`, `layered_architecture`, `stripe_webhook`, `scheduled_jobs`.

Each DIAG id → **config-only** pass + **live** pass (where safe) + **fail-closed** when dependency down.

---

## 10. Merchant portal — page / subpage matrix

| Route                                | Case IDs | Must cover                                                    |
| ------------------------------------ | -------- | ------------------------------------------------------------- |
| `/sign-in`, `/sign-up`               | M-UI-001 | Clerk org                                                     |
| `/onboarding`                        | M-UI-002 | Company file; activation policy                               |
| `/dashboard`                         | M-UI-010 | Own metrics only                                              |
| `/book`                              | M-UI-020 | Places + Valhalla quote; book → sync path                     |
| `/orders`, `/orders/[order_id]`      | M-UI-030 | Track façade; POD download                                    |
| `/bulk`                              | M-UI-040 | Exists for OWNER/ADMIN/OPS; under-nav OK (intentional)        |
| `/routes`, `/routes/[job_id]`        | M-UI-050 | Import ≠ fleet Optimize                                       |
| `/track`                             | M-UI-060 | Public-ish track UX via API                                   |
| `/billing`, `/billing/invoices/[id]` | M-UI-070 | Pay now / pay all; server amounts                             |
| `/shopify`                           | M-UI-080 | OAuth + carrier status                                        |
| `/api`                               | M-UI-090 | Create/rotate keys; docs                                      |
| `/team`                              | M-UI-100 | Seats                                                         |
| `/settings`                          | M-UI-110 | Profile/locations/alerts/branding — not invoices/keys/Shopify |
| `/reports`                           | M-UI-120 | Spend/channel/FSA bands                                       |
| `/notifications`                     | M-UI-130 | Prefs + inbox                                                 |
| `/referrals`                         | M-UI-140 | Credits                                                       |
| `/help`                              | M-UI-150 | Help                                                          |

**Negative:** merchant UI never hits Fleetbase, never uses Google for rates, never SocketCluster.

---

## 11. Driver surfaces & mobile handshake

| ID       | P   | Case                               | Expected                                                            | Seed                                  |
| -------- | --- | ---------------------------------- | ------------------------------------------------------------------- | ------------------------------------- |
| D-UI-001 | P0  | Mobile `handshake.ts` session gate | Clerk Bearer → `/driver-api/v1`; Fleetbase never direct             | `apps/mobile-driver/src/handshake.ts` |
| D-UI-002 | P0  | Driver web BFF `:3003`             | `/api/driver` → `/driver-api/v1`; **not** unified with mobile auth  | intentional dual path                 |
| D-UI-003 | P0  | Jobs list / accept / reject        | Via driver_engine → Fleetbase bridge                                | driver platform                       |
| D-UI-004 | P1  | Preview→Accept optimize            | `apply_on_ready=false` then Accept                                  | phase5/6                              |
| D-UI-005 | P1  | Offline queue optimize_route       | Only on network failure                                             | phase docs                            |
| D-UI-006 | P1  | FCM channels                       | Loud for assignments/critical                                       | NOTIF                                 |
| D-UI-007 | P1  | Location pings                     | Through PC API → Fleetbase track; no `POST /driver/location` legacy | removed endpoint test                 |
| D-UI-008 | P2  | Docs upload helper                 | Shared; Identity/Checkr CTAs web-first                              | intentional skip mobile CTAs          |
| D-UI-009 | P3  | Full Navigator clone               | **Assert not required**                                             | intentional skip                      |

---

## 12. Website / customer / lead ingest (cross-links)

| ID          | P   | Case                   | Notes                                        |
| ----------- | --- | ---------------------- | -------------------------------------------- |
| E2E-WEB-001 | P1  | Quote CTA → API quotes | Places + Valhalla; charter 15s test          |
| E2E-WEB-002 | P1  | Lead ingest webhooks   | Meta/Google/etc. → CRM bus                   | `test_lead_*` |
| E2E-CUS-*   | —   | Full retail matrix     | **See** `CUSTOMER_PERSONA_DEV_TEST_CASES.md` |

---

## 13. End-to-end development loops

| ID      | P   | Loop                                | Command / surface                               |
| ------- | --- | ----------------------------------- | ----------------------------------------------- |
| E2E-001 | P0  | P0 booking loop                     | `pnpm validate:p0:fast` then full `validate:p0` |
| E2E-002 | P0  | D3 matrix                           | `pnpm validate:e2e` / nightly `nightly-e2e.yml` |
| E2E-003 | P1  | Portal smoke                        | `pnpm validate:portal-smoke`                    |
| E2E-004 | P1  | Mobile smoke                        | `pnpm validate:mobile-smoke`                    |
| E2E-005 | P1  | Admin tablet ops                    | `pnpm validate:admin-tablet`                    |
| E2E-006 | P0  | Architecture gates                  | `pnpm validate:architecture`                    |
| E2E-007 | P0  | D2 contracts                        | `pnpm validate:d2`                              |
| E2E-008 | P1  | Integrations matrix                 | `pnpm validate:integrations-matrix`             |
| E2E-009 | P1  | Admin System Tests UI               | Run all DIAG ids against local stack            |
| E2E-010 | P1  | Mailpit glance after remind/receipt | Manual ops after SMTP path                      |

---

## 14. You-asked-for + missed surfaces (explicit)

Items you listed are covered above. **Also required** (easy to miss):

| Area                               | Why                             |
| ---------------------------------- | ------------------------------- |
| Event Bus + Redis streams          | Sync/notify spine               |
| SpiceDB                            | Authz SoT                       |
| Staff IdP (not only Clerk)         | Admin auth                      |
| Checkr + Stripe Identity           | Driver verification (flags)     |
| ZeptoMail                          | Prod email leave                |
| Doppler / project mode             | Fail-closed posture             |
| OpenAPI census + vendor leaves     | Prevent boundary rot            |
| Merchant partner API + idempotency | ERP ingress                     |
| NetSuite + Zapier                  | Non-Shopify ERP                 |
| Lead ingest bus (Meta/etc.)        | Growth handshakes               |
| Websocket live map (PC, not SC)    | Ops UX                          |
| Prometheus `/metrics`              | SLOs                            |
| Alembic + ORM ownership            | Schema discipline               |
| Worker queue depth probes          | Ops readiness                   |
| cuOpt shadow                       | Non-replacement optimize shadow |
| FSA / GTA150 coverage              | Pricing + tile honesty          |
| Sequence store CAS                 | Optimize apply races            |
| Public tracking snapshot           | Customer trust without auth     |
| Integrity / IDOR / tenant          | Network trust                   |
| Blog CMS / website SEO gates       | GTM (lower P for ops)           |

**Not in repo / do not invent product tests for:** WooCommerce, QuickBooks, SAP, custom SC clients, Google Distance Matrix, second VROOM client, Fleetbase Storefront/Ledger as PC SKU, Zoho SalesIQ, full Ontario tiles, mobile Critical Alerts entitlement — see intentional skips (assert absence where useful as ARCH/P3).

---

## 15. Implementation order (Jeff Dean)

1. **P0 handshakes:** FB-HS + FB-ENG sync/webhook + ARCH vendor leaves + SPA Valhalla/OSRM + AUTH portal triad + PAY checkout webhook.
2. **P0 execution:** VR optimize driver-scoped + POD + CT operations page smoke.
3. **P1 money/notify:** Shopify Quote≡Book, AR pay, FCM loud path, Mailpit.
4. **P1 matrices:** Admin/Merchant page load + DIAG full catalog.
5. **P2 polish:** reports, referrals, blog, chaos probes.
6. **P3:** only “assert still skipped” for intentional holds.

When coding a case: **CodeGraph** for schemas → **Ripwire** for thin router/adapter callers → write pytest next to seed files → wire into existing `validate:*` where it belongs. Do not start a fourth sensor or a parallel test framework.

---

## 16. Related SSOT

- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md)
- [FLEETBASE_PERMANENT_BOND.md](FLEETBASE_PERMANENT_BOND.md) — identity + adapter + handshake + heal
- [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md)
- [CUSTOMER_PERSONA_DEV_TEST_CASES.md](CUSTOMER_PERSONA_DEV_TEST_CASES.md)
- [MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md](MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md)
- `apps/api/src/porterchain_api/admin_engine/diagnostics_catalog.py` (`TEST_CATALOG`)
- `.cursor/rules/fleetbase-first-policy.mdc` · `graph-tools.mdc` · `porterchain-charter.mdc`
