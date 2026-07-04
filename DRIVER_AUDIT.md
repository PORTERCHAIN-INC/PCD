# Driver Portal — Architecture Audit

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Date:** June 30, 2026  
**Scope:** `apps/driver-portal/`, `apps/mobile-driver/`, `driver_engine/`, `/driver-api/v1/*`, `services/driver-platform/`, Fleetbase adapter driver methods  
**Method:** Source-code trace from UI → API → services → adapter → Fleetbase

**Status key:** ✅ Implemented · ⚠ Partial · ❌ Missing · 🚫 Violation

---

## 1. Locked topology compliance

Required flow per masterrule §1 and §7:

```
Driver Portal (:3003) / Mobile Driver (Expo)
    ↓ HTTPS
Porterchain API (:8001) — Logistics Orchestrator
    ↓
FastAPI Router — routers/driver.py (Controller)
    ↓
Application Service — porterchain_driver/* + driver_engine/*
    ↓
Repository → Porterchain PostgreSQL
    ↓ (logistics execution, when bridge enabled)
DriverFleetbaseBridge → Fleetbase Adapter → Fleetbase (:8000)
```

**Hard rule:** Driver App must **never** communicate directly with Porterchain business APIs that bypass orchestration, and must **never** call Fleetbase HTTP.

| Check                                   | Status | Evidence                                                                                                     |
| --------------------------------------- | ------ | ------------------------------------------------------------------------------------------------------------ |
| UIs call Porterchain API only           | ✅     | Portal: BFF proxy → `:8001/driver-api/v1/*`; Mobile: `EXPO_PUBLIC_API_URL` → `:8001`                         |
| No direct Fleetbase HTTP from UIs       | ✅     | Grep: no `:8000`, `FLEETBASE_*`, or Fleetbase URLs in `apps/driver-portal/src/` or `apps/mobile-driver/src/` |
| Routers delegate to services            | ✅     | `routers/driver.py` — thin controllers, `_platform` + `DriverAuthService`                                    |
| Business logic in `porterchain_driver/` | ✅     | 20 service modules under `services/driver-platform/`                                                         |
| Fleetbase via adapter only              | ✅     | `driver_engine/fleetbase_bridge.py` → `get_fleetbase_integration()`                                          |
| `fleetbase_driver_id` read-only in UI   | ✅     | Display field in mobile types only                                                                           |

**Fleetbase boundary verdict (UI):** ✅ **Compliant** — neither driver client talks to Fleetbase.

---

## 2. Already implemented

### 2.1 Frontend — Driver Portal (`apps/driver-portal/`)

| Feature                        | Route                   | API                                                  | Status |
| ------------------------------ | ----------------------- | ---------------------------------------------------- | ------ |
| Clerk + dev email login        | `/login`                | `POST /api/auth/login` → `/driver-api/v1/auth/login` | ✅     |
| httpOnly JWT session (BFF)     | `/api/auth/session`     | Cookie-based                                         | ✅     |
| Dashboard KPIs + online toggle | `/dashboard`            | `GET /dashboard`, `POST /availability`               | ✅     |
| Today's earnings               | `/earnings`             | `GET /earnings/today`                                | ✅     |
| Wallet + transactions          | `/wallet`               | `GET /wallet`                                        | ✅     |
| Assigned route (read-only)     | `/stops`                | `GET /routes/assigned`                               | ✅     |
| Performance metrics            | `/performance`          | `GET /performance`                                   | ✅     |
| Vehicle list                   | `/vehicle`              | `GET /vehicle`                                       | ✅     |
| Insurance compliance           | `/insurance`            | `GET /insurance`                                     | ✅     |
| Documents list                 | `/documents`            | `GET /documents`                                     | ✅     |
| Training modules list          | `/training`             | `GET /training`                                      | ✅     |
| Support tickets list           | `/support`              | `GET /support`                                       | ✅     |
| Emergency distress             | `/emergency`            | `POST /emergency`                                    | ✅     |
| Porterchain API proxy          | `/api/driver/[...path]` | Forwards to `:8001/driver-api/*`                     | ✅     |

### 2.2 Frontend — Mobile Driver (`apps/mobile-driver/`)

| Feature                   | Screen                 | API                                    | Status            |
| ------------------------- | ---------------------- | -------------------------------------- | ----------------- |
| Email login               | `LoginScreen`          | `POST /driver-api/v1/auth/login`       | ✅ (dev-oriented) |
| Dashboard + online toggle | `HomeScreen`           | `GET /dashboard`, `POST /availability` | ✅                |
| Profile                   | `ProfileScreen`        | `GET /me`                              | ✅                |
| FCM push registration     | `usePushNotifications` | `POST /push/register`                  | ✅                |
| Secure token storage      | `AuthContext`          | Bearer to Porterchain API              | ✅                |

### 2.3 Backend (`porterchain_driver/` + `driver_engine/`)

| Service / Module                                              | Responsibility                                          | Status              |
| ------------------------------------------------------------- | ------------------------------------------------------- | ------------------- |
| `DriverAuthService`                                           | Clerk-verified login, JWT issuance                      | ✅                  |
| `DriverFleetbaseBridge`                                       | Adapter wrapper — track, toggle, route, POD, state sync | ✅                  |
| `DriverOfflineExecutor`                                       | Replay queued offline actions                           | ✅ (foundation fix) |
| `DashboardService`                                            | Today's snapshot                                        | ✅                  |
| `EarningsService`                                             | Today/week/route earnings, delivery credit              | ✅                  |
| `WalletService`                                               | Balance, transactions, payouts                          | ✅                  |
| `StopsService`                                                | Routes, arrive, deliver, exceptions + Fleetbase sync    | ✅ (foundation fix) |
| `AvailabilityService`                                         | Online/offline, accept/reject + Fleetbase toggle        | ✅                  |
| `LocationService`                                             | GPS pings → DB + Fleetbase track                        | ✅                  |
| `ProofOfDeliveryService`                                      | OTP, photo/signature/barcode, complete + Fleetbase      | ✅ (foundation fix) |
| `NavigationService`                                           | Route polyline via Fleetbase + Google Maps URL          | ✅                  |
| `PushService`                                                 | Device registration via Notification Engine             | ✅                  |
| `EmergencyService`                                            | Distress → critical ticket + domain event               | ✅                  |
| `SupportService`, `IncidentService`, `DocumentsService`, etc. | Compliance & ops                                        | ✅                  |

### 2.4 API surface (`/driver-api/v1/*`)

| Area                                                      | Endpoints                                                           | Status                   |
| --------------------------------------------------------- | ------------------------------------------------------------------- | ------------------------ |
| Auth                                                      | `POST /auth/login`, `GET /me`                                       | ✅                       |
| Dashboard / earnings / wallet / bonuses                   | 6 endpoints                                                         | ✅                       |
| Availability / vehicle / insurance / documents / training | 8 endpoints                                                         | ✅                       |
| Support / incidents / emergency / push                    | 6 endpoints                                                         | ✅                       |
| Routes / stops / orders / navigation                      | 12 endpoints                                                        | ✅                       |
| POD capture                                               | 5 endpoints                                                         | ✅                       |
| Location                                                  | `POST /location` + legacy `POST /driver/location`                   | ✅                       |
| Offline queue                                             | `POST /offline/queue`, `GET /offline/pending`, `POST /offline/sync` | ✅ (sync foundation fix) |

### 2.5 Fleetbase integration path (driver execution)

| Stage                    | Component                                                           | Status              |
| ------------------------ | ------------------------------------------------------------------- | ------------------- |
| Driver approval sync     | `admin_engine/driver_service.py` → `BookingSyncService.sync_driver` | ✅                  |
| Online/offline toggle    | `availability.py` → `toggle_driver_online`                          | ✅                  |
| GPS track                | `location.py` → `track_driver_location`                             | ✅                  |
| POD upload               | `pod.py` → `upload_pod_*`                                           | ✅                  |
| Route polyline           | `navigation.py` → `fetch_route`                                     | ✅                  |
| Stop state → Fleetbase   | `stops.py` → `DriverFleetbaseBridge.sync_order_state`               | ✅ (foundation fix) |
| Route start → Fleetbase  | `start_route` → `start_order_execution`                             | ✅ (foundation fix) |
| POD complete → Fleetbase | `complete_pod` → `complete_order_execution`                         | ✅ (foundation fix) |
| Outbound status map      | `porterchain_fleetbase_adapter/events/lifecycle.py`                 | ✅ (foundation fix) |
| Inbound webhooks         | `routers/webhooks.py` → `WebhookProcessor`                          | ✅                  |

---

## 3. Partially implemented

| Area                               | What exists                                           | Gap                                                                                               |
| ---------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Driver portal UI**               | Read-heavy dashboard, compliance pages                | No stop execution (arrive, deliver, POD); no maps/navigation; no location background tracking     |
| **Mobile driver**                  | Home, profile, push, online toggle                    | No stops/POD/camera/maps; `expo-camera`, `expo-location`, `react-native-maps` in deps but unwired |
| **Mobile auth**                    | Email-only login                                      | No Clerk integration for production                                                               |
| **Stops / routes**                 | Synthetic `route-{date}` ID; pickup+dropoff per order | No real Fleetbase route entity binding                                                            |
| **Earnings**                       | Server-side `DEFAULT_PER_STOP_CENTS = 850`            | Not wired to `pricing_engine`                                                                     |
| **Performance**                    | `driver.performance` JSON                             | Defaults to 95%/98% placeholders when empty                                                       |
| **Documents / training / support** | Backend CRUD                                          | Portal read-only; no upload, complete, or create UI                                               |
| **Bonuses**                        | API + dashboard count                                 | No bonuses page or claim UI                                                                       |
| **Offline sync**                   | Queue, list, sync endpoint                            | No mobile offline queue client; no background worker (driver-initiated sync only)                 |
| **Refresh token**                  | Issued at login, stored in cookie                     | No refresh route in portal BFF                                                                    |
| **Path alias**                     | `apps/driver-portal/` + `apps/mobile-driver/` active  | `apps/driver/` remains README placeholder per §4.2                                                |

---

## 4. Missing

| Item                                          | masterrule / docs reference            | Priority                       |
| --------------------------------------------- | -------------------------------------- | ------------------------------ |
| Stop execution UI (arrive, deliver, POD)      | §5 Driver portal, `DRIVER_PLATFORM.md` | P0 — product, not architecture |
| Mobile Clerk auth (production login)          | §15 Security                           | P0 — product                   |
| Background GPS (`POST /location`) from mobile | §13 Fleetbase GPS                      | P1 — product                   |
| Driver payout batches                         | §11.2 billing                          | P2 — roadmap                   |
| Bonuses claim UI                              | `DRIVER_PLATFORM.md`                   | P2                             |
| Support/incident create UI                    | RBAC driver self-service               | P2                             |
| Document upload UI                            | Compliance workflow                    | P2                             |
| Training completion UI                        | Compliance workflow                    | P3                             |
| Live route map in portal                      | Navigation API exists                  | P3                             |
| Docker service entry for driver-portal        | Runs via `pnpm dev:driver` only        | P3                             |

---

## 5. Architecture violations

| ID     | Layer       | Violation                                                                     | Severity | Location                                  | Fix                                                       |
| ------ | ----------- | ----------------------------------------------------------------------------- | -------- | ----------------------------------------- | --------------------------------------------------------- |
| AV-D01 | Service     | `arrive_stop` / `deliver_stop` accepted `fleetbase_bridge` but did not use it | ⚠ Medium | `porterchain_driver/stops.py`             | ✅ Fixed — `sync_order_state` on transitions              |
| AV-D02 | Service     | `complete_pod` returned `fleetbase_synced=True` without adapter call          | ⚠ Medium | `porterchain_driver/pod.py`               | ✅ Fixed                                                  |
| AV-D03 | Service     | `OfflineService.sync_pending()` had no API trigger                            | ⚠ Medium | `offline.py`, `routers/driver.py`         | ✅ Fixed — `POST /offline/sync` + `DriverOfflineExecutor` |
| AV-D04 | Service     | `start_route` did not sync Fleetbase execution start                          | ⚠ Medium | `stops.py`, `routers/driver.py`           | ✅ Fixed                                                  |
| AV-D05 | Adapter     | No outbound Porterchain → Fleetbase status map                                | ⚠ Medium | `lifecycle.py`, `integration.py`          | ✅ Fixed — `PORTERCHAIN_STATE_TO_FLEETBASE_STATUS`        |
| AV-D06 | Mobile auth | Login sends email only — fails without `CLERK_DEV_BYPASS` in production       | ⚠ High   | `mobile-driver/src/services/driverApi.ts` | Open — product                                            |
| AV-D07 | Docs        | `DRIVER_PLATFORM.md` says JWT in `localStorage`; portal uses httpOnly cookies | ⚠ Low    | `DRIVER_PLATFORM.md:139`                  | Open — docs                                               |
| AV-D08 | UI          | Dashboard/mobile optimistic online toggle without error refetch               | ⚠ Low    | `dashboard/page.tsx`, `HomeScreen.tsx`    | Open — UX                                                 |

**No violations found:**

- UI → Fleetbase direct calls 🚫
- Business logic in React components (beyond display/formatting) 🚫
- Heavy business rules in `routers/driver.py` 🚫
- Pricing/earnings rules in UI 🚫
- Router → Fleetbase HTTP direct 🚫

---

## 6. Duplicate components

| Item                                                             | Assessment                                                  |
| ---------------------------------------------------------------- | ----------------------------------------------------------- |
| `apps/driver-portal/` vs `apps/mobile-driver/`                   | ✅ Intentional — web dashboard + mobile execution app       |
| `apps/driver/` README placeholder                                | ⚠ Path alias duplication per §4.2 — not active              |
| Legacy `POST /driver/location` vs `POST /driver-api/v1/location` | ⚠ Duplicate endpoint — backward compat for `CONNECTIONS.md` |
| Admin driver CRM vs Driver self-service                          | ✅ Intentional separation — different audiences             |

---

## 7. Duplicate APIs

| Endpoint pair                                             | Assessment                                        |
| --------------------------------------------------------- | ------------------------------------------------- |
| `POST /driver/location` vs `POST /driver-api/v1/location` | ⚠ Same handler logic — legacy alias               |
| `/driver-api/v1/*` vs `/v1/admin/drivers/*`               | ✅ Intentional — driver self-service vs staff CRM |

---

## 8. Business logic violations

| Check                         | Status | Notes                                                                                |
| ----------------------------- | ------ | ------------------------------------------------------------------------------------ |
| Earnings/wallet rules in UI   | ✅     | Server-side `EarningsService`, `WalletService`                                       |
| Order state transitions in UI | ✅     | Would go through API (execution UI not built yet)                                    |
| State machine in router       | ✅     | Router delegates to `StopsService` + `order_transitions`                             |
| Hardcoded earnings rate       | ⚠      | `DEFAULT_PER_STOP_CENTS = 850` in service — correct layer, should use pricing engine |
| Performance defaults          | ⚠      | Placeholder percentages when `driver.performance` empty                              |
| Training catalog in service   | ✅     | Static `_DEFAULT_MODULES` — acceptable for MVP                                       |

---

## 9. Fleetbase violations

| Rule (masterrule §2, §7, §13)                          | Status                                                           |
| ------------------------------------------------------ | ---------------------------------------------------------------- |
| Driver apps must never call Fleetbase                  | ✅ Verified by source grep                                       |
| Fleetbase owns execution only (dispatch, GPS, POD)     | ✅                                                               |
| Porterchain owns earnings, wallet, compliance, support | ✅                                                               |
| All Fleetbase HTTP via adapter                         | ✅                                                               |
| Commercial data not duplicated in Fleetbase            | ✅ `fleetbase_order_id` / `fleetbase_driver_id` correlation only |

| Concern                         | Detail                   | Severity | Fix       |
| ------------------------------- | ------------------------ | -------- | --------- |
| Stop arrive/deliver → Fleetbase | Bridge param was ignored | ⚠ Medium | ✅ Fixed  |
| `complete_pod` Fleetbase sync   | Misreported sync status  | ⚠ Medium | ✅ Fixed  |
| Dispatch start on route start   | Not wired                | ⚠ Medium | ✅ Fixed  |
| Driver entity sync              | Admin path only          | ✅       | By design |

---

## 10. Layer compliance matrix

| Layer               | Location                                    | Driver compliance                                    |
| ------------------- | ------------------------------------------- | ---------------------------------------------------- |
| UI (portal)         | `apps/driver-portal/`                       | ✅ Render + fetch; BFF for auth/proxy                |
| UI (mobile)         | `apps/mobile-driver/`                       | ✅ Thin client; production auth gap                  |
| Controller          | `routers/driver.py`                         | ✅ Thin; instantiates bridge per logistics endpoint  |
| Application service | `porterchain_driver/`                       | ✅ Primary business logic home                       |
| Engine bridge       | `driver_engine/`                            | ✅ Auth, RBAC, Fleetbase boundary, offline executor  |
| Adapter             | `services/fleetbase-adapter/`               | ✅ Track, toggle, POD, route, status, start/complete |
| Repository          | SQLAlchemy in services + `driver_models.py` | ✅ Monolith pattern                                  |

---

## 11. Security posture

| Control                                                  | Status                    |
| -------------------------------------------------------- | ------------------------- |
| Clerk JWT on portal login                                | ✅                        |
| httpOnly cookies for portal session                      | ✅                        |
| Porterchain JWT on `/driver-api/v1/*`                    | ✅                        |
| `require_approved_driver` on execution endpoints         | ✅                        |
| Mobile Clerk integration                                 | ❌ — email-only dev login |
| Dev bypass gated on `clerk_dev_bypass` / `app_env=local` | ✅                        |
| Secrets in env only                                      | ✅                        |

---

## 12. Observability

| Item                                               | Status                  |
| -------------------------------------------------- | ----------------------- |
| Domain events on availability, delivery, emergency | ✅                      |
| `fleetbase_synced` flag on POD responses           | ✅ (accurate after fix) |
| Driver portal-specific metrics                     | ⚠ None dedicated        |
| Correlation IDs via `RequestIdMiddleware`          | ✅                      |
| Fleetbase sync audit + retry queue (admin path)    | ✅                      |

---

## 13. UI ↔ API coverage matrix

| Backend endpoint                 | Portal         | Mobile |
| -------------------------------- | -------------- | ------ |
| `POST /auth/login`               | ✅             | ✅     |
| `GET /me`                        | ❌             | ✅     |
| `GET /dashboard`                 | ✅             | ✅     |
| `GET /earnings/today`            | ✅             | ❌     |
| `GET /wallet`                    | ✅             | ❌     |
| `GET /bonuses`                   | ⚠ (count only) | ❌     |
| `POST /bonuses/{id}/claim`       | ❌             | ❌     |
| `GET /performance`               | ✅             | ❌     |
| `POST /availability`             | ✅             | ✅     |
| `GET /routes/assigned`           | ✅ (read)      | ❌     |
| `POST /routes/{id}/start`        | ❌             | ❌     |
| `POST .../arrive`, `.../deliver` | ❌             | ❌     |
| POD endpoints (5)                | ❌             | ❌     |
| `POST /location`                 | ❌             | ❌     |
| `POST /offline/sync`             | ❌             | ❌     |
| `POST /emergency`                | ✅             | ❌     |
| `POST /push/register`            | ❌             | ✅     |

**Portal coverage:** ~16 of 41 endpoints (~39%, mostly GET).  
**Mobile coverage:** ~5 of 41 endpoints (~12%).

---

## 14. Compliance score

| Dimension                   | Score  | Notes                                             |
| --------------------------- | ------ | ------------------------------------------------- |
| Locked topology (UI)        | 98/100 | No Fleetbase leakage                              |
| Layered architecture        | 94/100 | Router/service split clean; foundation gaps fixed |
| Fleetbase boundary (server) | 92/100 | Stop→Fleetbase sync wired                         |
| Portal feature completeness | 40/100 | Dashboard/compliance reads; no execution          |
| Mobile feature completeness | 15/100 | Core shell + push only                            |
| Backend API completeness    | 90/100 | Broad surface; offline sync endpoint added        |
| Security                    | 72/100 | Portal Clerk ✅; mobile production auth ❌        |

**Overall driver surface: ~72/100** — architecture and backend topology are sound; UIs lag far behind the API, especially stops/POD/location.

---

## 15. Foundation fixes applied (this audit)

Architecture-only changes — no UI rebuild:

1. **`PORTERCHAIN_STATE_TO_FLEETBASE_STATUS`** in `services/fleetbase-adapter/.../events/lifecycle.py` — outbound status map per masterrule Appendix A.
2. **`FleetbaseAdapter.start_order_execution` / `complete_order_execution` / `update_order_status`** — adapter methods for driver execution sync.
3. **`DriverFleetbaseBridge.sync_order_state`** — maps Porterchain order states to Fleetbase actions.
4. **`StopsService`** — wires `fleetbase_bridge` on `start_route`, `arrive_stop`, `deliver_stop`.
5. **`ProofOfDeliveryService.complete_pod`** — accurate `fleetbase_synced` via adapter.
6. **`DriverOfflineExecutor`** + **`POST /driver-api/v1/offline/sync`** — replays queued offline actions through application services.

---

## 16. Related documents

| Document                                                               | Purpose                                                         |
| ---------------------------------------------------------------------- | --------------------------------------------------------------- |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md)                             | Driver platform design                                          |
| [masterrule.md](./masterrule.md)                                       | Source of truth                                                 |
| [ARCHITECTURE_ALIGNMENT_REPORT.md](./ARCHITECTURE_ALIGNMENT_REPORT.md) | Platform-wide alignment (§12 driver section is stale on mobile) |
| [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)                 | Adapter and sync flows                                          |
| [MERCHANT_AUDIT.md](./MERCHANT_AUDIT.md)                               | Parallel audit format                                           |

---

_Audit performed per masterrule §19 — search existing code before creating new modules; preserve locked topology; implement missing architecture only._
