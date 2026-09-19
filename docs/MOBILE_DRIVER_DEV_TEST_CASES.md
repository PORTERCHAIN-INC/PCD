# Mobile Driver (Expo) — development test cases (depth SSOT)

**Entry index:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md)  
**Sibling (web + admin drivers):** [DRIVER_ADMIN_DEV_TEST_CASES.md](DRIVER_ADMIN_DEV_TEST_CASES.md)  
**Integrations:** [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) · [MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md](MAPS_FIREBASE_PUSH_NOTIF_DEV_TEST_CASES.md) · [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md)  
**Auth depth:** [AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md](AUTHENTICATION_DRIVER_ADMIN_DEV_TEST_MATRIX.md)  
**Policy holds (not bugs):** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md) · [DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md](DRIVER_VERIFICATION_INTENTIONAL_SKIPS.md)

**Interactive catalog:** [mobile-driver-dev-test-cases.canvas.tsx](/Users/ravi/.cursor/projects/Users-ravi-Documents-GitHub-PCD/canvases/mobile-driver-dev-test-cases.canvas.tsx)

**Mapped:** 2026-09-17 via **Graphify** (`query` driver mobile↔Fleetbase, `explain` App.tsx / fleetbase_bridge / communications, `god-nodes`).  
**Sensor note:** This session used **Graphify only** (one sensor / session). Next moments:

| Next | Tool                                       | Use for                                                                      |
| ---- | ------------------------------------------ | ---------------------------------------------------------------------------- |
| B    | CodeGraph `codegraph_explore`              | Pydantic `Driver*` responses, POD/offline payloads, MapsService nav shapes   |
| C    | Ripwire `--for` / `--callers` / `--impact` | Thin `routers/driver/*`, `handshake.ts`, `push.ts`, Fleetbase adapter leaves |

**App root:** `apps/mobile-driver` (Expo SDK 57) · API prefix `/driver-api/v1` on `:8001` · **never** Fleetbase `:8000` / SocketCluster from the device.

**Charter gate:** Cases protect capacity execution (accept→arrive→POD), GPS→Fleetbase SoT, FCM assignment, offline integrity, money (wallet/COD). Reject rebuilds of Fleetbase dispatch / VROOM / Google routing.

---

## 0. Topology (Graphify SSOT)

```
apps/mobile-driver (Expo)
  SessionGate / Clerk Bearer  ──►  :8001 /driver-api/v1/*   (thin routers/driver/*)
                                         │
                                    driver_engine + porterchain_driver (driver-platform)
                                         │
                    ┌────────────────────┼────────────────────┐
                    ▼                    ▼                    ▼
           FleetbaseAdapter      MapsService           NotificationEngine
           (GPS SoT, assign,     Valhalla→OSRM         FCM DeviceService
            POD mirror, VROOM    (nav/ETA)             Mailpit/Zepto email
            via Fleetbase only)  Google = Places/tiles
                                 NEVER Distance Matrix
```

**Dual path (intentional):** Driver **web** BFF `:3003` `/api/driver` ≠ mobile Bearer. Do not unify (ARCH-MD-001).

**God-node magnets:** `Driver` (188 edges), `Order`/`OrderState`, `Settings`, `get_driver_context`.

---

## 1. ID scheme

| Prefix       | Layer                                                     |
| ------------ | --------------------------------------------------------- |
| `MD-HS-*`    | Boot / handshake / health / force-update                  |
| `MD-AUTH-*`  | Clerk · SessionGate · invite · device unlock · dev-login  |
| `MD-SCR-*`   | Screens (every `Screen` + `FieldTab`)                     |
| `MD-UI-*`    | Shared UI modules (`ui/*`, shell, scanners)               |
| `MD-FILE-*`  | Client modules (`api`, `offline`, `push`, `maps`, …)      |
| `MD-API-*`   | Every `/driver-api/v1` op used by mobile                  |
| `MD-ENG-*`   | `driver_engine` / `porterchain_driver` services           |
| `MD-FB-*`    | Fleetbase bridge / GPS / assignment / POD sync            |
| `MD-MAP-*`   | Valhalla · OSRM · VROOM (via FB) · Google Places/deeplink |
| `MD-PUSH-*`  | Expo → FCM register / loud assignment                     |
| `MD-MAIL-*`  | Invite / SOS / support email (Mailpit local)              |
| `MD-PAY-*`   | COD Checkout · wallet ledger read                         |
| `MD-SHOP-*`  | Shopify order on route (indirect)                         |
| `MD-ERP-*`   | Partner/ERP-sourced jobs on driver surface                |
| `MD-DB-*`    | Driver ORM / offline queue / wallet rows                  |
| `MD-DOC-*`   | Docker · compose health · EAS                             |
| `MD-MAE-*`   | Maestro flows under `apps/mobile-driver/maestro/`         |
| `MD-ARCH-*`  | Negatives / intentional skips                             |
| `MD-CHAOS-*` | Failure scenarios                                         |

**Priority:** P0 ship-blocker · P1 trust/money/execution · P2 polish · P3 depth / policy hold.

**Coverage tags in canvas:** `gap` · `partial` · `covered` · `skip`.

---

## 2. Surface inventory (files & screens)

### 2.1 Screens (`Screen` union)

| Screen             | File                                                       | Primary APIs                                           |
| ------------------ | ---------------------------------------------------------- | ------------------------------------------------------ |
| `force-update`     | `ForceUpdateScreen.tsx`                                    | `GET /health/status` → `mobile.driver.min_version`     |
| `invite`           | `InviteScreen.tsx`                                         | deep link `/auth/driver-invite` · Clerk bind           |
| `sign-in`          | `SignInScreen.tsx`                                         | Clerk / `auth/dev-login` (local) · handshake           |
| `onboarding`       | `OnboardingScreen.tsx`                                     | `GET /onboarding` · `POST /documents` · verification\* |
| `route` (tab work) | `RouteScreen.tsx`                                          | nav session/route · arrive/deliver · POD · location    |
| `job-detail`       | `JobDetailScreen.tsx`                                      | `GET /jobs/{id}` · accept/reject · scan · COD          |
| `inbox`            | `InboxScreen.tsx`                                          | communications notifications\*                         |
| `support`          | `SupportScreen.tsx`                                        | support hub/claims/emergency · SOS                     |
| (via tabs)         | `JobsScreen` · `MoneyScreen` · `DocsScreen` · `MoreScreen` | jobs\* · wallet/earnings · docs · profile/more         |

### 2.2 Field tabs

| Tab     | Host        | Assert                                                            |
| ------- | ----------- | ----------------------------------------------------------------- |
| `work`  | RouteScreen | Next stop + StatusRail from handshake                             |
| `jobs`  | JobsScreen  | Assigned-only; optimize preview/accept/undo                       |
| `money` | MoneyScreen | Wallet + earnings + statements (read)                             |
| `docs`  | DocsScreen  | Upload + status badges                                            |
| `more`  | MoreScreen  | Profile, vehicle, training, bonuses, ratings, inbox/support entry |

### 2.3 Client modules (must have ≥1 case)

| Module                                                                    | Responsibility                                                                  |
| ------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `api.ts`                                                                  | All `driverFetch` → `:8001` only                                                |
| `handshake.ts`                                                            | Aggregates me/dashboard/jobs/nav/push/location                                  |
| `session.ts` / `auth/SessionGate.tsx`                                     | Bearer required                                                                 |
| `auth/deviceUnlock.ts`                                                    | Biometric gate                                                                  |
| `offline.ts`                                                              | Queue + flush + `runOnlineOrQueue`                                              |
| `push.ts` / `pushToken.ts`                                                | Expo collect → **FCM registration token** only                                  |
| `location.ts` / `locationTask.ts`                                         | Foreground + background pings                                                   |
| `maps.ts`                                                                 | Turn-by-turn deeplink (external maps) — not Google DM                           |
| `pod.ts` / `ui/PodCapture.tsx` / `SignaturePad`                           | Photo/sig/barcode/OTP                                                           |
| `docsUpload.ts`                                                           | Doc upload helper                                                               |
| `linking.ts` / `hooks/useDriverDeepLinks.ts`                              | Invite + `/jobs/{id}`                                                           |
| `hooks/useFieldSession.ts` · `useEnterRoute.ts` · `completeStopAction.ts` | Session/route/stop orchestration                                                |
| `gate.ts` · `version.ts` · `config.ts`                                    | Feature gates / min version / env                                               |
| `ui/*`                                                                    | FieldShell, TabBar, StatusRail, BarcodeScanner, FieldOpsPanel, AppErrorBoundary |

### 2.4 Backend packages in path

| Package                                         | Role                                                                                                                              |
| ----------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `routers/driver/*`                              | Thin FastAPI (`profile`, `dashboard`, `shift`, `jobs`, `navigation_pod`, `communications`, `support`, `verification`, `auth_dev`) |
| `driver_engine/*`                               | Auth, onboarding, verification, wallet_ledger, fleetbase_bridge, offline_executor, api_service                                    |
| `services/driver-platform/porterchain_driver/*` | jobs, pod, push, location, navigation, offline, wallet, shift, …                                                                  |
| `fleetbase-adapter`                             | GPS SoT, assignment, POD mirror, orchestrator/VROOM                                                                               |
| `MapsService`                                   | Valhalla → OSRM                                                                                                                   |
| `notification_engine`                           | DeviceService FCM + DeliveryService                                                                                               |
| Worker                                          | EventBus + Fleetbase retry queue                                                                                                  |

---

## 3. P0 handshake — `MD-HS-*` (run first)

| ID        | P   | Case                               | Expected                                        | Seed / how         |
| --------- | --- | ---------------------------------- | ----------------------------------------------- | ------------------ |
| MD-HS-001 | P0  | Cold launch probes `/health`       | API `up` or honest `down` in handshake          | `probeApi`         |
| MD-HS-002 | P0  | `GET /health/status` mobile policy | Soft/force update via `ForceUpdateScreen`       | health status      |
| MD-HS-003 | P0  | Handshake never targets `:8000`    | Only `apiBaseUrl` (:8001)                       | static + Maestro   |
| MD-HS-004 | P0  | Handshake after sign-in            | `auth=up`, driver name, availability            | `refreshHandshake` |
| MD-HS-005 | P0  | Nav bits from MapsService          | ETA/distance labels; no Google DM               | nav session        |
| MD-HS-006 | P0  | Push probe in handshake            | FCM token path or `unavailable` honest          | `collectPush`      |
| MD-HS-007 | P0  | Location idle → granted            | Permission UX; denied still allows offline read | location           |
| MD-HS-008 | P1  | Platform status from health        | Degraded Fleetbase/Maps labeled                 | public health      |
| MD-HS-009 | P1  | Offline note after flush           | Pending count matches queue                     | offline flush      |
| MD-HS-010 | P0  | Web BFF ≠ mobile Bearer            | Dual path intentional                           | ARCHITECTURE       |

---

## 4. Auth — `MD-AUTH-*`

| ID          | P   | Case                             | Expected                        |
| ----------- | --- | -------------------------------- | ------------------------------- |
| MD-AUTH-001 | P0  | No Bearer → API 401              | `driver_auth_required`          |
| MD-AUTH-002 | P0  | Valid Clerk driver triad         | `DriverContext`                 |
| MD-AUTH-003 | P0  | Merchant/customer JWT            | 401/403                         |
| MD-AUTH-004 | P0  | Suspended driver                 | 403 `driver_suspended`          |
| MD-AUTH-005 | P0  | Unlinked Clerk user              | 403 `driver_not_found`          |
| MD-AUTH-006 | P0  | SessionGate blocks shell         | Until token present             |
| MD-AUTH-007 | P0  | Dev-login only local             | Prod rejects `/auth/dev-login`  |
| MD-AUTH-008 | P1  | Invite deep link                 | Token → Clerk bind → onboarding |
| MD-AUTH-009 | P1  | Device unlock                    | Biometric fail stays locked     |
| MD-AUTH-010 | P1  | Email mismatch Clerk vs Driver   | 403                             |
| MD-AUTH-011 | P0  | Exclusive clerk id portal=driver | Cross-portal bind blocked       |
| MD-AUTH-012 | P2  | Sign-out clears push unregister  | Best-effort `push/unregister`   |

---

## 5. Screens & UX — `MD-SCR-*`

### 5.1 Boot / gate

| ID         | P   | Screen                | Assert                                               |
| ---------- | --- | --------------------- | ---------------------------------------------------- |
| MD-SCR-001 | P0  | ForceUpdate           | Below `min_version` + `force_update` blocks continue |
| MD-SCR-002 | P1  | ForceUpdate soft      | Soft allows continue; banner once                    |
| MD-SCR-003 | P0  | SignIn                | Renders `mobile-sign-in`; no Fleetbase URL text      |
| MD-SCR-004 | P0  | SignIn error          | Handshake error surface; retry                       |
| MD-SCR-005 | P0  | Invite                | Invalid token honest error                           |
| MD-SCR-006 | P0  | Onboarding incomplete | Cannot reach route until ready (prod)                |
| MD-SCR-007 | P2  | Onboarding skip       | Dev-only `onboarding-skip-dev`                       |

### 5.2 Work / route

| ID         | P   | Case                  | Assert                                           |
| ---------- | --- | --------------------- | ------------------------------------------------ |
| MD-SCR-010 | P0  | Route empty           | Honest empty; no fake stops                      |
| MD-SCR-011 | P0  | Next stop rail        | Matches handshake nextStop/type                  |
| MD-SCR-012 | P0  | Arrive                | `POST .../arrive` then refresh                   |
| MD-SCR-013 | P0  | Deliver/complete stop | Via `completeStopAction` + POD                   |
| MD-SCR-014 | P0  | Open turn-by-turn     | `maps.openTurnByTurn` external; nav_url from API |
| MD-SCR-015 | P0  | Exception report      | Exception types posted; ops notified             |
| MD-SCR-016 | P1  | Break / resume        | Shift break surfaces on rail                     |
| MD-SCR-017 | P1  | Offline queue badge   | Pending >0 when down                             |
| MD-SCR-018 | P1  | Barcode scanner modal | Scan → `pod-barcode` / package scan              |
| MD-SCR-019 | P1  | Signature pad         | Captures → `pod-signature`                       |
| MD-SCR-020 | P0  | POD photo             | Camera/file → `pod-photo`                        |
| MD-SCR-021 | P0  | OTP when required     | `generateOtp` + `pod-complete`                   |
| MD-SCR-022 | P1  | SOS                   | `POST /emergency` risk path only                 |
| MD-SCR-023 | P2  | FieldOpsPanel         | Controls match shift/availability                |

### 5.3 Jobs

| ID         | P   | Case                         | Assert                                           |
| ---------- | --- | ---------------------------- | ------------------------------------------------ |
| MD-SCR-030 | P0  | Jobs list                    | Assigned-only; IDOR impossible                   |
| MD-SCR-031 | P0  | Accept / reject              | Legal transitions only                           |
| MD-SCR-032 | P0  | Job detail                   | Stops, COD CTA, scan phases                      |
| MD-SCR-033 | P0  | Package scan pickup/delivery | ScanGateService progress                         |
| MD-SCR-034 | P1  | COD checkout                 | Returns Checkout URL; existing Checkout unbroken |
| MD-SCR-035 | P1  | Optimize preview             | Enqueues Fleetbase/VROOM — **no local TSP**      |
| MD-SCR-036 | P1  | Optimize accept / undo       | Version conflict → `sequence_version_conflict`   |
| MD-SCR-037 | P1  | Jobs history                 | Read-only past jobs                              |
| MD-SCR-038 | P2  | Deep link `/jobs/{id}`       | Opens JobDetail                                  |

### 5.4 Money / docs / more / inbox / support

| ID         | P   | Case                        | Assert                         |
| ---------- | --- | --------------------------- | ------------------------------ |
| MD-SCR-040 | P1  | Wallet                      | Ledger read; no invent payouts |
| MD-SCR-041 | P1  | Earnings today / statements | CSV download headers           |
| MD-SCR-042 | P1  | Bonuses claim               | Idempotent claim               |
| MD-SCR-043 | P1  | Docs upload                 | Types validated; badges        |
| MD-SCR-044 | P2  | Vehicle photos              | `profile/vehicle-photos`       |
| MD-SCR-045 | P2  | Training complete           | Module mark                    |
| MD-SCR-046 | P2  | Ratings / performance       | Snapshot only                  |
| MD-SCR-047 | P1  | Inbox read/archive/mark-all | Notification engine            |
| MD-SCR-048 | P1  | Support ticket / claim      | Category `driver_support`      |
| MD-SCR-049 | P1  | Emergency contact CRUD      | PUT persists                   |
| MD-SCR-050 | P1  | Incidents report            | Creates incident row           |
| MD-SCR-051 | P2  | Insurance / vehicle cards   | Expiry surfaces                |
| MD-SCR-052 | P0  | Error boundary              | Crash → recover shell          |
| MD-SCR-053 | P1  | TabBar navigation           | 5 tabs preserve handshake      |

---

## 6. Client files — `MD-FILE-*`

| ID          | P   | File                    | Assert                                                 |
| ----------- | --- | ----------------------- | ------------------------------------------------------ |
| MD-FILE-001 | P0  | `api.ts`                | Timeout + Bearer + detail parse; base `/driver-api/v1` |
| MD-FILE-002 | P0  | `api.ts`                | No hardcoded Fleetbase host                            |
| MD-FILE-003 | P0  | `handshake.ts`          | Composes me+dashboard+jobs+nav; failure partial OK     |
| MD-FILE-004 | P0  | `offline.ts`            | Queue → sync → retry failed                            |
| MD-FILE-005 | P0  | `push.ts`               | Rejects registering Expo push token as FCM             |
| MD-FILE-006 | P0  | `locationTask.ts`       | Background task registered before App mount            |
| MD-FILE-007 | P1  | `maps.ts`               | Deeplink only; never Distance Matrix SDK               |
| MD-FILE-008 | P1  | `pod.ts`                | Offline-capable POD enqueue                            |
| MD-FILE-009 | P1  | `linking.ts`            | Invite + job universal links                           |
| MD-FILE-010 | P1  | `completeStopAction.ts` | Arrive→POD→deliver ordering                            |
| MD-FILE-011 | P2  | `version.ts`            | Semver compare for force update                        |
| MD-FILE-012 | P2  | `gate.ts`               | Feature flags fail closed                              |
| MD-FILE-013 | P1  | `docsUpload.ts`         | Upload URL then `POST /documents`                      |
| MD-FILE-014 | P2  | `format.ts`             | Currency/km labels consistent                          |
| MD-FILE-015 | P0  | `config.ts`             | `apiBaseUrl` from env; timeout bounded                 |

---

## 7. Driver API census — `MD-API-*`

Prefix: `/driver-api/v1`. Auth: Clerk Bearer (or gated dev-login).

### 7.1 Profile / onboarding / verification

| ID         | P   | Method path             | Expected                                  |
| ---------- | --- | ----------------------- | ----------------------------------------- |
| MD-API-001 | P0  | `GET /me`               | Profile + wallet_cents (no mapper shadow) |
| MD-API-002 | P0  | `GET /onboarding`       | Checklist gates                           |
| MD-API-003 | P1  | `GET /profile`          | Extended profile                          |
| MD-API-004 | P1  | `GET                    | POST /verification/identity*`             | Session; **never auto-APPROVE** |
| MD-API-005 | P1  | `GET                    | POST /verification/background*`           | Checkr; human approve only      |
| MD-API-006 | P1  | `GET                    | POST /verification/abstract*`             | Abstract submit                 |
| MD-API-007 | P0  | `POST /auth/dev-login`  | Local only                                |
| MD-API-008 | P2  | `GET /auth/dev-drivers` | Local picker                              |

### 7.2 Dashboard / money / shift

| ID         | P   | Method path                                            | Expected                                      |
| ---------- | --- | ------------------------------------------------------ | --------------------------------------------- |
| MD-API-010 | P0  | `GET /dashboard`                                       | Shift + next job summary                      |
| MD-API-011 | P1  | `GET /wallet`                                          | Ledger ownership `driver_engine`              |
| MD-API-012 | P1  | `GET /earnings` · `/today` · `/statements*` · download | CSV OK                                        |
| MD-API-013 | P1  | `GET /bonuses` · `POST .../claim`                      |                                               |
| MD-API-014 | P1  | `GET /performance` · `/ratings`                        |                                               |
| MD-API-015 | P0  | `POST /availability`                                   | online/offline/busy/idle → Fleetbase presence |
| MD-API-016 | P0  | `GET                                                   | POST /shift*` start/end/break/resume          |     |

### 7.3 Jobs / routes / location / COD

| ID         | P   | Method path                                                  | Expected                       |
| ---------- | --- | ------------------------------------------------------------ | ------------------------------ |
| MD-API-020 | P0  | `GET /jobs` · `/jobs/{id}` · `/history`                      | Assigned-only                  |
| MD-API-021 | P0  | `POST /orders/{id}/accept\|reject`                           |                                |
| MD-API-022 | P0  | `POST /location`                                             | Fleetbase GPS SoT — not PC SoT |
| MD-API-023 | P0  | `GET /routes/assigned` · `POST .../start` · stops · earnings |                                |
| MD-API-024 | P0  | `POST .../arrive` · `/deliver` · `/exception`                |                                |
| MD-API-025 | P0  | `POST /orders/{id}/packages/scan`                            | ScanGate                       |
| MD-API-026 | P1  | `POST /orders/{id}/cod-checkout`                             | StripeCodService               |
| MD-API-027 | P1  | `POST /jobs/optimize*` · accept · undo                       | Via Fleetbase VROOM            |
| MD-API-028 | P0  | IDOR other driver job                                        | 403/404                        |

### 7.4 Navigation / POD / offline

| ID         | P   | Method path                                                      | Expected                   |
| ---------- | --- | ---------------------------------------------------------------- | -------------------------- |
| MD-API-030 | P0  | `GET /navigation/session` · `/route` · `/orders/{id}/navigation` | Valhalla→OSRM              |
| MD-API-031 | P0  | `POST .../pod-photo\|signature\|barcode\|complete`               |                            |
| MD-API-032 | P0  | `POST /orders/{id}/otp`                                          |                            |
| MD-API-033 | P0  | `POST /offline/queue` · `GET pending` · `POST sync`              |                            |
| MD-API-034 | P1  | Offline optimize alias                                           | Labeled; no in-process TSP |

### 7.5 Communications / support / docs / misc

| ID         | P   | Method path                                               | Expected                                     |
| ---------- | --- | --------------------------------------------------------- | -------------------------------------------- |
| MD-API-040 | P0  | `POST /push/register\|unregister`                         | FCM-only token validation                    |
| MD-API-041 | P1  | `GET /communications*` notifications history/read/archive |                                              |
| MD-API-042 | P1  | `GET /communications/offline` · `POST .../retry`          |                                              |
| MD-API-043 | P1  | `GET                                                      | POST /support*` · claims · emergency-contact |     |
| MD-API-044 | P1  | `GET                                                      | POST /incidents`·`POST /emergency`           |     |
| MD-API-045 | P1  | `GET                                                      | POST /documents` · vehicle-photos            |     |
| MD-API-046 | P2  | `GET /vehicle` · `/insurance` · `/training*`              |                                              |

**OpenAPI live probe:** keep `scripts/verify_driver_api_live.py` green (~40 probes).  
Prefer `DRIVER_API_DRIVER_ID=<onboarded-uuid>` locally — see §19.1 (Bearer `dev` may hit onboarding 403).

---

## 8. Engines & microservices — `MD-ENG-*`

| ID         | P   | Unit                                      | Assert                                                 |
| ---------- | --- | ----------------------------------------- | ------------------------------------------------------ |
| MD-ENG-001 | P0  | `DriverApiService.require_assigned_order` | Guards mutate paths                                    |
| MD-ENG-002 | P0  | `DriverFleetbaseBridge`                   | Mutating sync enqueued — no request-path block forever |
| MD-ENG-003 | P0  | `offline_executor`                        | Replays queued actions idempotently                    |
| MD-ENG-004 | P1  | `wallet_ledger`                           | Only engine writes ledger rows                         |
| MD-ENG-005 | P1  | `onboarding_service`                      | Checklist coherent with mobile                         |
| MD-ENG-006 | P1  | `verification_service`                    | Status badges; no auto APPROVE                         |
| MD-ENG-007 | P0  | `porterchain_driver.jobs`                 | List/detail/optimize façade                            |
| MD-ENG-008 | P0  | `porterchain_driver.pod`                  | Media + complete                                       |
| MD-ENG-009 | P0  | `porterchain_driver.location`             | Forward to Fleetbase                                   |
| MD-ENG-010 | P0  | `porterchain_driver.push`                 | Delegates DeviceService                                |
| MD-ENG-011 | P1  | `porterchain_driver.navigation`           | MapsService only                                       |
| MD-ENG-012 | P1  | `ScanGateService`                         | QR parse ownership                                     |
| MD-ENG-013 | P1  | `StripeCodService`                        | COD issue for assigned order                           |
| MD-ENG-014 | P2  | Thin routers LOC                          | Under allowlist; logic in services                     |

---

## 9. Fleetbase — `MD-FB-*`

| ID        | P   | Case                              | Expected                              |
| --------- | --- | --------------------------------- | ------------------------------------- |
| MD-FB-001 | P0  | Approve driver → `push_driver`    | Public id stored                      |
| MD-FB-002 | P0  | Assignment webhook → job appears  | Mobile refresh/push                   |
| MD-FB-003 | P0  | Location → Fleetbase GPS SoT      | PC not SoT                            |
| MD-FB-004 | P0  | POD complete mirrored             | Adapter path                          |
| MD-FB-005 | P0  | Mobile never calls `:8000`        | vendor-leaves CI                      |
| MD-FB-006 | P0  | No SocketCluster in Expo          | Import ban                            |
| MD-FB-007 | P1  | Adapter circuit / retry           | Sync job + worker drain               |
| MD-FB-008 | P1  | Availability → Fleetbase presence | online/offline                        |
| MD-FB-009 | P1  | Optimize run via orchestrator     | VROOM inside Fleetbase                |
| MD-FB-010 | P2  | Chaos `fleetbase_offline`         | Mobile queues offline; honest degrade |

---

## 10. Maps / VROOM / Google — `MD-MAP-*`

| ID         | P   | Case                                | Expected                   |
| ---------- | --- | ----------------------------------- | -------------------------- |
| MD-MAP-001 | P0  | Nav route Valhalla-first            | OSRM fallback labeled      |
| MD-MAP-002 | P0  | No Google Distance Matrix / ETA API | ARCH + static              |
| MD-MAP-003 | P1  | Google Places unused on driver nav  | Tiles/deeplink OK only     |
| MD-MAP-004 | P0  | No PorterChain VROOM HTTP client    | Optimize via Fleetbase     |
| MD-MAP-005 | P1  | VROOM_ROUTER=valhalla in Fleetbase  | Probe orchestrator engines |
| MD-MAP-006 | P1  | Chaos valhalla_failure → OSRM       | Degrade path               |
| MD-MAP-007 | P1  | Chaos osrm_failure                  | Honest error in nav        |
| MD-MAP-008 | P2  | External maps deeplink coords       | Match dest lat/lng         |

---

## 11. Push / Firebase / email / notify — `MD-PUSH-*` / `MD-MAIL-*`

| ID          | P   | Case                                | Expected                  |
| ----------- | --- | ----------------------------------- | ------------------------- |
| MD-PUSH-001 | P0  | Register FCM token                  | DeviceService accepts     |
| MD-PUSH-002 | P0  | Reject Expo / `web-*` / APNs-as-FCM | 400 InvalidFcmToken       |
| MD-PUSH-003 | P0  | Assignment loud push                | FCM when token else email |
| MD-PUSH-004 | P1  | Unregister on logout                | Token revoked             |
| MD-PUSH-005 | P1  | Inbox in_app milestones             | Alert budget intentional  |
| MD-PUSH-006 | P1  | Firebase offline chaos              | Queue + email fallback    |
| MD-MAIL-001 | P1  | Driver invite → Mailpit             | Activation link           |
| MD-MAIL-002 | P1  | SOS / support email                 | DeliveryService           |
| MD-MAIL-003 | P2  | Zepto prod path                     | Not asserted on local     |

---

## 12. Money / Shopify / ERP — `MD-PAY-*` / `MD-SHOP-*` / `MD-ERP-*`

| ID          | P   | Case                                | Expected                             |
| ----------- | --- | ----------------------------------- | ------------------------------------ |
| MD-PAY-001  | P0  | COD Checkout issue                  | Stripe Checkout URL; webhook settles |
| MD-PAY-002  | P0  | Existing retail Checkout unbroken   | Freeze lift additive only            |
| MD-PAY-003  | P1  | Wallet ledger immutable from mobile | Read-only                            |
| MD-SHOP-001 | P1  | Shopify-origin order on route       | Same job UX; source badge optional   |
| MD-SHOP-002 | P2  | Carrier quote ≠ driver optimize     | No Shopify→VROOM confusion           |
| MD-ERP-001  | P1  | Partner API / OAuth booked job      | Driver sees assigned job only        |
| MD-ERP-002  | P2  | Merchant webhook-created order      | Same Fleetbase assignment path       |
| MD-ERP-003  | P3  | Future ERP adapters                 | Catalog only — no fake green         |

**Missed integrations explicitly covered above:** Clerk, Fleetbase, Firebase/FCM, Valhalla, OSRM, VROOM (via FB), Google Maps (Places/deeplink only), Mailpit/email, notification_engine, Stripe COD, Shopify (indirect), partner/ERP ingest, worker retry, Docker health.

**Also assert (often forgotten):**

| Extra                    | Case                                                |
| ------------------------ | --------------------------------------------------- |
| Redis                    | Session/rate limits don't break mobile Bearer       |
| Postgres 18              | Migrations head; integrity FKs                      |
| Valkey (Fleetbase cache) | Dispatch presence unaffected by PC Redis            |
| Sentry                   | Mobile + API error boundary breadcrumbs             |
| EAS / app.json           | Bundle id `com.porterchain.PCD`; FCM plists present |
| Deep links               | Universal links registered                          |
| Background location      | OS permission + task name stable                    |
| Sequence version         | Optimize conflict messaging                         |

---

## 13. Database — `MD-DB-*`

| ID        | P   | Area                           | Assert                         |
| --------- | --- | ------------------------------ | ------------------------------ |
| MD-DB-001 | P0  | `Driver` / `Vehicle` ownership | Writes via allowlisted engines |
| MD-DB-002 | P0  | Offline action rows            | Idempotent client_id           |
| MD-DB-003 | P1  | Wallet ledger                  | `driver_engine/wallet_ledger`  |
| MD-DB-004 | P1  | NotificationRecord / devices   | Persona=driver                 |
| MD-DB-005 | P1  | FleetbaseSyncJob on fail       | RetryQueue                     |
| MD-DB-006 | P2  | Incidents / support tickets    | FK integrity                   |

---

## 14. Docker / EAS — `MD-DOC-*`

| ID         | P   | Case                              | Expected                                     |
| ---------- | --- | --------------------------------- | -------------------------------------------- |
| MD-DOC-001 | P0  | Compose API `:8001` healthy       | Mobile can probe                             |
| MD-DOC-002 | P0  | Image pins exact                  | No `:latest`                                 |
| MD-DOC-003 | P0  | Valhalla `:8002` · OSRM `:5000`   | Maps degrade tests                           |
| MD-DOC-004 | P0  | Fleetbase `:8000` + VROOM sidecar | Optimize path                                |
| MD-DOC-005 | P1  | Mailpit up                        | Invite email                                 |
| MD-DOC-006 | P1  | Redis 8.8                         | Worker + sessions                            |
| MD-DOC-007 | P1  | EAS profiles                      | `eas.json` preview/production                |
| MD-DOC-008 | P2  | Android/iOS Firebase configs      | Present; not committed secrets beyond public |

---

## 15. Maestro — `MD-MAE-*`

| ID         | P   | Flow                   | Assert                         |
| ---------- | --- | ---------------------- | ------------------------------ |
| MD-MAE-001 | P0  | `login-and-track.yaml` | Sign-in → route `mobile-track` |
| MD-MAE-002 | P1  | `scan-offline.yaml`    | Queue while offline; sync      |
| MD-MAE-003 | P1  | `pod-capture.yaml`     | Photo/sig path                 |
| MD-MAE-004 | P1  | `deeplink-job.yaml`    | Opens job                      |
| MD-MAE-005 | P2  | `onboarding-skip.yaml` | Dev skip only                  |

### 15.1 Device prerequisites (local)

| Platform | Need                                                               | Verified 2026-09-17 on this machine                                                                                          |
| -------- | ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| Android  | SDK + **AVD with system image** + `adb devices` shows `emulator-*` | SDK present; **`~/.android/avd` empty**; `system-images/` empty — create AVD in Android Studio → Device Manager              |
| iOS      | Xcode **Simulator.app** + runtime + booted sim                     | `xcode-select` OK; **Simulator.app missing**; CoreSimulatorService broken — install Simulator via Xcode Settings → Platforms |

```bash
# After AVD exists:
$ANDROID_HOME/emulator/emulator -avd <AVD_NAME> -netdelay none -netspeed full &
adb wait-for-device
# Install Expo/dev build for com.porterchain.PCD, then:
maestro test apps/mobile-driver/maestro/login-and-track.yaml
```

`appId: com.porterchain.PCD` (see `app.json` ios.bundleIdentifier / android.package).

---

## 16. Architecture negatives — `MD-ARCH-*`

| ID          | P   | Assert absence / hold                                          |
| ----------- | --- | -------------------------------------------------------------- |
| MD-ARCH-001 | P0  | No unify web BFF auth with mobile Bearer                       |
| MD-ARCH-002 | P0  | No PorterChain VROOM client                                    |
| MD-ARCH-003 | P0  | No Google Distance Matrix for nav/pricing                      |
| MD-ARCH-004 | P0  | No SocketCluster / Fleetbase HTTP from Expo                    |
| MD-ARCH-005 | P0  | No GPS SoT rebuilt in PC                                       |
| MD-ARCH-006 | P0  | No auto `DriverStatus.APPROVED` from Identity/Checkr           |
| MD-ARCH-007 | P1  | Identity/Checkr deep CTAs may stay web-first (**SKIP-POLICY**) |
| MD-ARCH-008 | P1  | Customer mobile depth intentional skip (not driver)            |
| MD-ARCH-009 | P1  | No live `DRIVER_*` toggles in Admin UI (env-only)              |

---

## 17. Chaos — `MD-CHAOS-*`

| ID           | P   | Scenario                   | Mobile expect                                   |
| ------------ | --- | -------------------------- | ----------------------------------------------- |
| MD-CHAOS-001 | P0  | `fleetbase_offline`        | Offline queue; no crash                         |
| MD-CHAOS-002 | P0  | `clerk_offline`            | Sign-in fail honest                             |
| MD-CHAOS-003 | P0  | `firebase_offline`         | Push unavailable; email fallback                |
| MD-CHAOS-004 | P1  | `valhalla_failure`         | OSRM or labeled fail                            |
| MD-CHAOS-005 | P1  | `osrm_failure`             | Honest nav error                                |
| MD-CHAOS-006 | P1  | `google_maps_failure`      | Deeplink may fail; routing still PC MapsService |
| MD-CHAOS-007 | P1  | `driver_rejects` / cancels | Capacity freed; ops sees                        |
| MD-CHAOS-008 | P1  | `vehicle_breakdown`        | Exception + support                             |
| MD-CHAOS-009 | P2  | Token revoke mid-shift     | Re-auth gate                                    |
| MD-CHAOS-010 | P2  | Sequence version conflict  | User-visible conflict string                    |

---

## 18. Implementation order (Jeff Dean)

1. **MD-HS-*** + **MD-AUTH-*** green on localhost.
2. **MD-API-020…034** jobs/POD/offline/location (pytest + live probe).
3. **MD-FB-*** + **MD-MAP-*** vendor leaves CI.
4. **MD-PUSH-*** / DeviceService FCM-only.
5. **MD-SCR-*** Maestro P0/P1 flows.
6. Money/COD/Shopify-indirect.
7. Verification CTAs per intentional skips.
8. Chaos drills in System Test Center.

### How to add a case

1. Graphify / CodeGraph / Ripwire (one moment).
2. Prefer pytest for API/engine; Maestro for `MD-SCR` / `MD-MAE`.
3. Link seed file in the table.
4. Never fail CI on `MD-ARCH-*` policy holds.

---

## 19. Seeds already green (expand, don’t duplicate)

| Area           | Seeds                                                                                                                                                  |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| P0 catalog     | `apps/api/tests/test_driver_p0_catalog.py` (17)                                                                                                        |
| Live API       | `scripts/verify_driver_api_live.py` (~40)                                                                                                              |
| Verification   | `test_driver_identity_verification.py`, `test_driver_background_check.py`, `test_driver_abstract_and_expiry.py`, `test_driver_verification_sources.py` |
| GPS            | `test_gps_ingest_wave01.py`, `wave3`, `wave4`                                                                                                          |
| Push/maps gaps | `test_maps_firebase_push_gaps.py`                                                                                                                      |
| Notifications  | `test_notification_*.py`                                                                                                                               |
| Fleetbase      | `test_fleetbase_*.py`, approve-push wave2                                                                                                              |
| Arch CI        | `verify_architecture_boundaries`, `verify_vendor_leaves`, model ownership, no ops spatial math                                                         |

### 19.1 Live probe auth seed (`DRIVER_API_DRIVER_ID`)

`scripts/verify_driver_api_live.py` defaults to `Authorization: Bearer dev`. That path binds **`.first()` APPROVED** driver (`get_driver_context`) — often **not** onboarding-ready → `403 driver_onboarding_blocked:…` on `/dashboard`, `/jobs`, `/jobs/history` (gate working; seed incomplete).

**Local fix (preferred for smoke):** target an onboarded driver via header bypass (no Bearer):

```bash
# Example: marco@porterchain.com after local compliance flags/docs are set
export DRIVER_API_DRIVER_ID=<uuid>   # e.g. 4cd33451-327b-4dbf-a02f-bddbb1e1e259
cd apps/api && source .venv/bin/activate
PYTHONPATH=src:../../shared/python:../../services/python:../../services/fleetbase-adapter:../../services/pricing-engine:../../services/event-bus:../../services/driver-platform \
  python ../../scripts/verify_driver_api_live.py
# expect: PASS: 40 probes accepted
```

| Env                    | Effect                                                                    |
| ---------------------- | ------------------------------------------------------------------------- |
| `DRIVER_API_BASE`      | default `http://127.0.0.1:8001`                                           |
| `DRIVER_API_TOKEN`     | default `dev` (used only when `DRIVER_API_DRIVER_ID` unset)               |
| `DRIVER_API_DRIVER_ID` | sends `X-Driver-Id` instead of Bearer — requires `CLERK_DEV_BYPASS` local |

**Do not** treat onboarding 403 on an incomplete seed as an API regression. Cases: `MD-SCR-006`, `MD-API-010`, `MD-AUTH-*`.

**Maestro UI:** `apps/mobile-driver/maestro/*.yaml` · `appId: com.porterchain.PCD` · needs booted Android emulator **or** iOS Simulator + app installed.

---

## 20. Coverage map (nothing orphaned)

| You asked for                     | Section    |
| --------------------------------- | ---------- |
| Each page / subpage / tab         | §2 · §5    |
| Each file / module                | §2.3 · §6  |
| API / FastAPI / microservices     | §7 · §8    |
| Fleetbase handshakes              | §9 · §3    |
| Firebase / push / notify / email  | §11        |
| Clerk                             | §4         |
| VROOM / Valhalla / OSRM / Google  | §10        |
| Backend / UI / UX / models / DB   | §5–8 · §13 |
| Docker / architecture             | §14 · §16  |
| Shopify / ERP / other connections | §12        |
| COD / wallet / Stripe             | §12        |
| Maestro                           | §15        |
| Chaos                             | §17        |
