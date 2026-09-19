# Driver + Admin drivers — development test cases

**Entry SSOT:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Integrations / Fleetbase:** [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md).  
**Optimize depth:** [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md).

**Interactive catalog (filter by persona / layer / P0–P3):** Cursor canvas  
[driver-admin-dev-test-cases.canvas.tsx](/Users/ravi/.cursor/projects/Users-ravi-Documents-GitHub-PCD/canvases/driver-admin-dev-test-cases.canvas.tsx).

**Mobile Expo depth SSOT:** [MOBILE_DRIVER_DEV_TEST_CASES.md](MOBILE_DRIVER_DEV_TEST_CASES.md) · canvas  
[mobile-driver-dev-test-cases.canvas.tsx](/Users/ravi/.cursor/projects/Users-ravi-Documents-GitHub-PCD/canvases/mobile-driver-dev-test-cases.canvas.tsx)  
(`MD-*` IDs — every screen/file/`/driver-api/v1` op + Fleetbase/Maps/FCM/COD/Shopify-ERP). This file keeps web + admin; do not fork a third mobile master.

**Sensors:** Graphify (architecture) → CodeGraph (schemas) → Ripwire (thin routers) — **one per session**.  
**Policy SSOT:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) — do not treat policy holds as test failures.

---

## Surfaces under test

| Persona       | App                          | Entry                                                                            |
| ------------- | ---------------------------- | -------------------------------------------------------------------------------- |
| Driver web    | `apps/driver-portal` `:3003` | BFF `/api/driver` → `/driver-api/v1`                                             |
| Driver mobile | `apps/mobile-driver` Expo    | Clerk Bearer → `:8001` `/driver-api/v1`                                          |
| Admin         | `apps/admin`                 | `/drivers`, `/drivers/[id]` (13 tabs), Settings driver modals, AssignDriverModal |

### Driver web pages

`/login` · `/onboarding` · `/dashboard` · `/jobs` · `/jobs/[orderId]` · `/navigation` · `/shift` · `/communications` · `/earnings` · `/wallet` · `/performance` · `/profile` · `/documents` · `/insurance` · `/vehicle` · `/training` · `/support` · `/emergency` · `/stops`

### Admin driver 360 tabs

`overview` · `identity` · `documents` · `vehicles` · `orders` · `performance` · `wallet` · `incidents` · `activities` · `tasks` · `timeline` · `analytics` · `settings`

### Prefixes

| Prefix        | Layer                                        |
| ------------- | -------------------------------------------- |
| `AUTH-D-*`    | Clerk driver / admin RBAC `drivers`          |
| `UI-D-*`      | Driver web pages                             |
| `UI-A-DRV-*`  | Admin drivers list + 360 tabs                |
| `API-D-*`     | `/driver-api/v1/*`                           |
| `API-A-DRV-*` | `/v1/admin/drivers*`                         |
| `FB-D-*`      | Fleetbase push_driver / GPS SoT / assignment |
| `MAP-D-*`     | Nav Valhalla→OSRM; no Google routing         |
| `NOTIF-D-*`   | FCM register + assignment push               |
| `DB-D-*`      | `driver_models` / Driver ORM                 |
| `MOB-D-*`     | Expo shells + Maestro                        |
| `ARCH-D-*`    | Negatives / intentional skips                |

**Priority:** P0 ship-blocker · P1 trust/money/execution · P2 polish · P3 intentional depth.

---

## P0 implementation order (gaps first)

1. **Auth** — Clerk bind (`get_driver_context`), admin RBAC module `drivers`, invite + Mailpit, dev-login prod gate.
2. **Admin lifecycle** — create/approve/suspend/reject/rehire + Fleetbase `push_driver`/`push_vehicle`.
3. **Driver jobs** — accept/reject/arrive/deliver/scan/COD + `require_assigned_order`.
4. **Navigation/POD/offline** — Valhalla→OSRM; POD; offline queue; no Google Distance Matrix.
5. **GPS + FCM** — location → Fleetbase SoT; `POST /push/register`; assignment fanout.
6. **Portal/admin UI Playwright** — AccessGate; list/bulk; SettingsTab.
7. **Mobile Maestro** — `login-and-track`, `scan-offline`, `pod-capture`, `deeplink-job`.
8. **CI gates** — model ownership, thin routers, D2, no ops spatial math, compose pins.

---

## Auth & RBAC — `AUTH-D-*`

| ID         | P   | Case                                        | Expected                               | Seed               |
| ---------- | --- | ------------------------------------------- | -------------------------------------- | ------------------ |
| AUTH-D-001 | P0  | Unauthenticated `/dashboard`                | Redirect `/login`                      | portal AccessGate  |
| AUTH-D-002 | P0  | Driver Clerk JWT on `/driver-api/v1`        | 200 with context; wrong portal key 401 | clerk registry     |
| AUTH-D-003 | P0  | Merchant JWT on driver API                  | 401/403                                | cross-portal       |
| AUTH-D-004 | P0  | Admin without `drivers` module              | 403 on `/v1/admin/drivers`             | hybrid RBAC        |
| AUTH-D-005 | P0  | Dev-login blocked when `APP_ENV` production | reject Bearer `dev`                    | config production  |
| AUTH-D-006 | P1  | Invite email → Mailpit                      | activation link binds Clerk            | invitation_service |
| AUTH-D-007 | P1  | Web BFF vs mobile Bearer stay separate      | intentional dual path                  | ARCHITECTURE       |

---

## Driver web UI — `UI-D-*` (every page smoke)

| ID       | P   | Route                                         | Assert                                         |
| -------- | --- | --------------------------------------------- | ---------------------------------------------- |
| UI-D-001 | P0  | `/login`                                      | Clerk sign-in renders; no Fleetbase URL        |
| UI-D-002 | P0  | `/onboarding`                                 | Gates incomplete docs; cannot reach jobs       |
| UI-D-003 | P0  | `/dashboard`                                  | Shift/job summary from API only                |
| UI-D-004 | P0  | `/jobs`                                       | Assigned-only list; empty state honest         |
| UI-D-005 | P0  | `/jobs/[orderId]`                             | Accept/reject/arrive/deliver; COD CTA when due |
| UI-D-006 | P0  | `/navigation`                                 | Polyline via MapsService; Places tiles OK      |
| UI-D-007 | P1  | `/stops`                                      | Sequence matches applied optimize              |
| UI-D-008 | P1  | `/shift`                                      | Clock in/out; offline flag                     |
| UI-D-009 | P1  | `/documents`                                  | Upload helper; verification badges             |
| UI-D-010 | P1  | `/vehicle` · `/insurance`                     | Expiry surfaces; revoke on lapse               |
| UI-D-011 | P1  | `/wallet` · `/earnings` · `/performance`      | Ledger read-only; no invent payouts            |
| UI-D-012 | P1  | `/communications` · `/support` · `/emergency` | Inbox + SOS risk path only                     |
| UI-D-013 | P2  | `/profile` · `/training`                      | Profile bind; training optional                |

---

## Admin drivers UI — `UI-A-DRV-*`

| ID           | P   | Case                                                  | Expected                                              |
| ------------ | --- | ----------------------------------------------------- | ----------------------------------------------------- |
| UI-A-DRV-001 | P0  | `/drivers` list                                       | Search/filter/status; no SocketCluster                |
| UI-A-DRV-002 | P0  | Create driver                                         | Invite + Mailpit; Fleetbase push on approve           |
| UI-A-DRV-003 | P0  | Approve / suspend / reject / rehire                   | Human `DriverStatus` only                             |
| UI-A-DRV-004 | P0  | 360 `overview`                                        | Next actions heuristic — not fake AI SKU              |
| UI-A-DRV-005 | P0  | 360 `identity`                                        | Stripe Identity / Checkr / abstract **source badges** |
| UI-A-DRV-006 | P1  | 360 `documents` / `vehicles`                          | Expiry + revoke                                       |
| UI-A-DRV-007 | P1  | 360 `orders` / `performance` / `wallet`               | Scoped reads                                          |
| UI-A-DRV-008 | P1  | 360 `incidents` / `activities` / `tasks` / `timeline` | Audit trail                                           |
| UI-A-DRV-009 | P2  | 360 `analytics` / `settings`                          | Feature flags env-only (no live DRIVER_* UI toggle)   |
| UI-A-DRV-010 | P0  | AssignDriverModal from Operations                     | CT assign → Fleetbase assignment push                 |

---

## Driver API — `API-D-*`

| ID        | P   | Case                               | Expected                                     | Seed                |
| --------- | --- | ---------------------------------- | -------------------------------------------- | ------------------- |
| API-D-001 | P0  | List jobs                          | Only assigned                                | driver jobs         |
| API-D-002 | P0  | Accept / reject / arrive / deliver | Legal `OrderState` only                      | status translator   |
| API-D-003 | P0  | Scan / POD                         | ScanGateService; media path                  | d3 POD / pod-media  |
| API-D-004 | P0  | IDOR other driver’s job            | 404/403                                      | `test_idor.py`      |
| API-D-005 | P1  | COD checkout issue                 | StripeCodService; Checkout unbroken          | COD                 |
| API-D-006 | P1  | Wallet ledger read                 | `driver_engine` ownership                    | wallet              |
| API-D-007 | P1  | Docs upload                        | Identity/Checkr/abstract flags               | verification suites |
| API-D-008 | P0  | Location ingest                    | Fleetbase GPS SoT — not PC ping store as SoT | gps_ingest waves    |
| API-D-009 | P1  | Push register                      | FCM token only; reject Expo/fake `web-*`     | DeviceService       |
| API-D-010 | P2  | Offline optimize alias             | Labeled offline; no in-process TSP           | offline optimize    |

---

## Admin driver API — `API-A-DRV-*`

| ID            | P   | Case                            | Expected                                   | Seed                                  |
| ------------- | --- | ------------------------------- | ------------------------------------------ | ------------------------------------- |
| API-A-DRV-001 | P0  | Create + approve                | `push_driver` / `push_vehicle` via adapter | wave2 approve                         |
| API-A-DRV-002 | P0  | Suspend/reject                  | Capacity removed; sync job                 | drivers_admin                         |
| API-A-DRV-003 | P1  | Driver360 board payload         | Tabs data coherent                         | driver360 / service coverage          |
| API-A-DRV-004 | P1  | Verification sources            | Badges from Identity/Checkr/abstract       | `test_driver_verification_sources.py` |
| API-A-DRV-005 | P1  | Compliance expiry sweep         | Flag-gated revoke                          | abstract_and_expiry                   |
| API-A-DRV-006 | P0  | Never auto-APPROVE from webhook | Status stays human                         | intentional skip assert               |

---

## Fleetbase / Maps / Notify — `FB-D-*` / `MAP-D-*` / `NOTIF-D-*`

| ID          | P   | Case                                       | Expected                            |
| ----------- | --- | ------------------------------------------ | ----------------------------------- |
| FB-D-001    | P0  | Approve → adapter push                     | Public id stored; retry on fail     |
| FB-D-002    | P0  | Assignment webhook → driver job            | Inbox/FCM fanout                    |
| FB-D-003    | P0  | Portal never calls `:8000` / SocketCluster | vendor-leaves CI                    |
| MAP-D-001   | P0  | Nav route Valhalla-first                   | OSRM fallback labeled; no Google DM |
| MAP-D-002   | P1  | Matrix scoring in CT                       | MapsService public APIs only        |
| NOTIF-D-001 | P0  | Assignment loud push                       | FCM when token; else email          |
| NOTIF-D-002 | P1  | Routine milestone stays in_app             | Alert budget (intentional)          |

---

## Database — `DB-D-*`

| ID       | P   | Model / area                                              | Assert                             |
| -------- | --- | --------------------------------------------------------- | ---------------------------------- |
| DB-D-001 | P0  | `Driver` / `Vehicle` (`admin_models`)                     | Writes via owning engine allowlist |
| DB-D-002 | P0  | `driver_models` (wallet, shift, docs, offline, incidents) | Ownership guard green              |
| DB-D-003 | P1  | `FleetbaseSyncJob` on driver push fail                    | RetryQueue row                     |
| DB-D-004 | P1  | Alembic integrity FKs                                     | Migrate head; smoke                |

---

## Mobile — `MOB-D-*` (summary; depth → MOBILE_DRIVER)

| ID        | P   | Case                                      | Expected                                             |
| --------- | --- | ----------------------------------------- | ---------------------------------------------------- |
| MOB-D-001 | P0  | Handshake types hit `:8001` only          | No `:8000` / fleetbase HTTP / SC → **MD-HS-***       |
| MOB-D-002 | P0  | Maestro login-and-track                   | Green on local → **MD-MAE-001**                      |
| MOB-D-003 | P1  | scan-offline / pod-capture / deeplink-job | Queue sync on reconnect → **MD-MAE-002..004**        |
| MOB-D-004 | P3  | Identity/Checkr CTAs                      | **SKIP-POLICY** — web only for now → **MD-ARCH-007** |

Full Expo matrix (screens, `api.ts` ops, Fleetbase/Valhalla/OSRM/VROOM/FCM/Clerk/COD/Shopify/ERP/Docker/chaos): [MOBILE_DRIVER_DEV_TEST_CASES.md](MOBILE_DRIVER_DEV_TEST_CASES.md).

---

## Architecture negatives — `ARCH-D-*`

| ID         | P   | Assert absence / hold                                            |
| ---------- | --- | ---------------------------------------------------------------- |
| ARCH-D-001 | P0  | No PorterChain VROOM client under `*_engine`                     |
| ARCH-D-002 | P0  | No Google Distance Matrix for nav/pricing                        |
| ARCH-D-003 | P0  | No auto `DriverStatus.APPROVED` from Identity/Checkr             |
| ARCH-D-004 | P0  | No unify web BFF auth with mobile Bearer                         |
| ARCH-D-005 | P1  | No Admin settings UI for live `DRIVER_*` / `CHECKR_*` (env-only) |
| ARCH-D-006 | P1  | No GPS SoT rebuilt in PorterChain                                |

---

## Scaffolded (2026-09-17)

| Layer                    | Path                                                                      | How to run                                                                   |
| ------------------------ | ------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| Registry SSOT            | [`docs/testing/driver_p0_registry.json`](testing/driver_p0_registry.json) | Flip `status` skeleton→implemented when body filled                          |
| Pytest P0                | `apps/api/tests/test_driver_p0_*.py`                                      | `cd apps/api && .venv/bin/pytest -m driver_p0 -q`                            |
| Playwright admin drivers | `apps/admin/e2e/drivers.p0.spec.ts`                                       | `pnpm --filter @porterchain/admin test:e2e:p0 -- e2e/drivers.p0.spec.ts`     |
| Playwright driver portal | `apps/driver-portal/e2e/*.p0.spec.ts`                                     | `pnpm --filter @porterchain/driver-portal test:e2e:install && … test:e2e:p0` |
| Maestro mobile           | `apps/mobile-driver/maestro/p0-*.yaml`                                    | `pnpm --filter @porterchain/mobile-driver test:maestro:p0`                   |
| Live API smoke           | `scripts/verify_driver_api_live.py`                                       | API on `:8001` + `Bearer dev`                                                |

---

## Started (2026-09-17)

| Suite                                      | Result                                                                                                                        |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `apps/api/tests/test_driver_p0_catalog.py` | **17 passed** (lifecycle, assigned-order, no auto-APPROVE, dev-login gate, OpenAPI, no VROOM client, `/me` shadow regression) |
| Existing `test_driver_*.py` verification   | green                                                                                                                         |
| `scripts/verify_driver_api_live.py`        | **PASS 40 probes** (API on `:8001`)                                                                                           |
| Bug fixed while running                    | `routers/driver/profile.py` — `def driver_profile` shadowed mapper → GET `/me` 500 on `wallet_cents`                          |

---

## Already covered (keep green)

| Area                                  | Tests / gates                                                                                                                                          |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Identity / Checkr / abstract / expiry | `test_driver_identity_verification.py`, `test_driver_background_check.py`, `test_driver_abstract_and_expiry.py`, `test_driver_verification_sources.py` |
| GPS ingest                            | `test_gps_ingest_wave01.py`, `test_gps_ingest_wave3.py`                                                                                                |
| Driver360 service                     | `test_service_coverage_batch3.py`, `test_extended_service_coverage.py`, `test_wave4_batch_g.py`                                                        |
| Approve → Fleetbase                   | `test_approve_driver_pushes_fleetbase_*` in `test_wave2_customers.py`                                                                                  |
| Arch CI                               | `verify_model_ownership`, thin-router LOC, D2, `verify_no_ops_spatial_math`                                                                            |

---

## Chaos / failure scenarios (driver-critical)

From `diagnostics_chaos` + `e2e_validation_catalog.FAILURE_SCENARIOS`:

`fleetbase_offline` · `fleetbase_adapter_failure` · `clerk_offline` · `firebase_offline` / `firebase_failure` · `google_maps_failure` · `osrm_failure` · `valhalla_failure` · `driver_rejects` · `driver_cancels` · `driver_offline` · `vehicle_breakdown`

---

## How to implement a case

1. CodeGraph extract schemas for the endpoint/model.
2. Ripwire `--callers` / `--impact` on the thin router or adapter symbol.
3. Add pytest next to seed files; wire Playwright/Maestro only for UI-D / MOB-D.
4. Never assert an intentional skip as a product bug.
