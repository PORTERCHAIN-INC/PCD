# Maps · Firebase · Push · Notifications ↔ Fleetbase — development test cases

**Status:** living catalog for **local / CI development** (not Doppler prod soak).  
**Role:** Deep slice for Google Maps (Places/tiles), Firebase FCM, browser/mobile push, `notification_engine`, and how those surfaces **connect (and correctly do not connect)** to Fleetbase.  
**Parent index:** [DEVELOPMENT_TEST_CASES.md](DEVELOPMENT_TEST_CASES.md).  
**Siblings:** [SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md](SYSTEM_INTEGRATIONS_DEV_TEST_CASES.md) · [DEV_TEST_CASES_FULL_STACK.md](DEV_TEST_CASES_FULL_STACK.md) · [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md).  
**Policy holds:** [PCD_INTENTIONAL_SKIPS.md](PCD_INTENTIONAL_SKIPS.md).

**Mapped:** 2026-09-17 via **full sensor pipeline** (one tool at a time):

| Moment | Tool                                       | Anchors used                                                                                                                                                                                                  |
| ------ | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| A      | Graphify CLI                               | `query` FCM/Maps/Fleetbase/Clerk/Shopify · `explain` `notification_admin_service` / `fcm_service` / `delivery_service` · `path` firebase↔fleetbase (**no directed edge — correct**) · `god-nodes`             |
| B      | CodeGraph CLI `explore`                    | `DeviceService` · `FCMService` · `MapsService` · `NotificationDevice` · `ClerkClaims` · `FleetbaseClient` · `ShopifyShop` · `ErpFulfillmentAdapter`                                                           |
| C      | Ripwire `--for` / `--expand` / `--callers` | `TEST_CATALOG` · `FAILURE_SCENARIOS` · `CHAOS_SCENARIOS` · `register_device` · `push_health` · `registerBrowserPush` · maps UI (`AddressAutocompleteInput`, `LiveMapPanel`, `OrderRouteMap`, `TrackRouteMap`) |

Do **not** invent cases that reopen intentional skips (Google Distance Matrix, Firebase Auth, PC VROOM client, SocketCluster in web, second mail/FCM engine).

---

## 0. Architecture truth (must stay true in every case)

```
Portals / Expo
  │ Places autocomplete + map tiles          │ FCM token + permission UX
  │ (Google JS only)                         │ registerBrowserPush / registerPush
  ▼                                          ▼
packages/maps + portal lib/*          POST /v1/notifications/devices/register
                                      POST /driver-api/v1/.../push (driver)
                                             │
                                             ▼
                                      DeviceService → NotificationDevice (Postgres)
                                             │
Order / Claim / Ticket / Ops events ──► notification_engine
                                             │
                         ┌───────────────────┼───────────────────┐
                         ▼                   ▼                   ▼
                    FCMService          DeliveryService      Email (SMTP→Mailpit
                    (Firebase)          (prefs + fanout)      / ZeptoMail prod)
                         │
                         ▼
              Admin PushHealthStrip ← GET /v1/admin/notifications/push-health

Spatial (pricing / ETA / CT scoring) — SEPARATE lane:
  MapsService → Valhalla :8002 → OSRM :5000  (never Google for distance/ETA/matrix)

Execution (dispatch / GPS SoT / POD / VROOM) — SEPARATE lane:
  *_engine → fleetbase-adapter → Fleetbase :8000 (+ VROOM sidecar)
  Portals NEVER call Fleetbase HTTP or SocketCluster.

Graphify: no directed path firebase → fleetbase  (notifications do not talk to Fleetbase).
Handshake to Fleetbase for notify is INDIRECT:
  Fleetbase webhook / sync → Order status → EventBus → notification_engine → FCM/email.
```

**Charter gate:** cases protect trust (POD/ETA honesty), utilization (loud push for assign), and fail-closed degrade — not UI chrome.

---

## 1. ID scheme (this catalog)

| Prefix                    | Layer                                                      |
| ------------------------- | ---------------------------------------------------------- |
| `MF-HS-*`                 | Cross-lane handshakes (Maps ↔ PC ↔ FB ↔ FCM)               |
| `GMAP-*`                  | Google Places + tiles + portal map chrome                  |
| `SPA-*`                   | Valhalla / OSRM / MapsService (spatial — not Google)       |
| `FCM-*`                   | Firebase credentials, FCMService, token validity           |
| `PUSH-*`                  | Browser SW / Expo / driver register / revoke               |
| `NE-*`                    | `notification_engine` models/services/processor            |
| `NA-*`                    | Admin notification APIs + PushHealthStrip + inbox          |
| `FB-NF-*`                 | Fleetbase → Order → notify (indirect connection)           |
| `UI-GMAP-*` / `UI-PUSH-*` | Page/subpage matrix for maps & push                        |
| `DIAG-*` / `CHAOS-*`      | System Tests + chaos (Ripwire SSOT)                        |
| `ARCH-*`                  | Negative / vendor-leaf contracts                           |
| `GAP-*`                   | Ripwire/CodeGraph **untested** hotspots to implement first |

**Priority:** P0 ship-blocker · P1 trust/ops · P2 regression · P3 assert-still-skipped.

Each case: **Precondition → Steps → Expected · Seed**.

---

## 2. Gap board (implement these pytest/UI cases first)

Ripwire/CodeGraph findings — expand existing seeds; do not duplicate blindly.

| ID     | P   | Gap                                                                            | Evidence                                | Seed / target                                                                                                              |
| ------ | --- | ------------------------------------------------------------------------------ | --------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| GAP-01 | P0  | `registerBrowserPush` has **0 indexed test callers** (admin + merchant)        | Ripwire `--callers=registerBrowserPush` | **Done** — admin + merchant `e2e/push.p0.spec.ts` + `__PC_TEST_FCM_TOKEN__` (live: `ADMIN_RUN_LIVE` / `MERCHANT_E2E_LIVE`) |
| GAP-02 | P0  | `InvalidFcmToken` / fake `web-*` / Expo token rejected at API                  | CodeGraph `DeviceService.register`      | **Seeded** `test_maps_firebase_push_gaps.py::test_gap02_*`                                                                 |
| GAP-03 | P1  | `FCMService` only 1/5 hop_tested                                               | Ripwire callers                         | **Seeded** `test_gap03_fcm_send_unconfigured_log_only` (+ existing loud-push FCM test)                                     |
| GAP-04 | P1  | `push_health` strip fields vs API contract                                     | Ripwire expand `push_health`            | **Done** — API `test_gap04_*` + UI wire `test_mf_hs_open_batch::test_na02_*` + Playwright strip                            |
| GAP-05 | P1  | `decodePolyline` cloned 3× (admin/driver/merchant/packages)                    | Ripwire clone=1                         | **Done** — portals re-export `@porterchain/maps`; `test_gap05_*`                                                           |
| GAP-06 | P1  | Chaos `firebase_offline` / `google_maps_failure` vs `FAILURE_SCENARIOS` naming | Ripwire `CHAOS_SCENARIOS` vs catalog    | **Done** — `CHAOS_ALIASES` + `resolve_chaos_scenario`; `test_gap06_*`                                                      |
| GAP-07 | P2  | Merchant `NotificationCenter.enablePush` path                                  | Ripwire                                 | **Done** — `test_gap07_*` + `apps/merchant-portal/e2e/push.p0.spec.ts` (live: `MERCHANT_E2E_LIVE=1`)                       |
| GAP-08 | P2  | Driver mobile `collectPush` / `registerPush`                                   | Ripwire                                 | **Done** — `test_driver_push_service.py` + Maestro `p0-push-register.yaml`                                                 |

---

## 3. Cross-lane handshakes — `MF-HS-*`

| ID       | P   | Case                                                                                                        | Expected                                                                | Seed                                                        |
| -------- | --- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- | ----------------------------------------------------------- |
| MF-HS-01 | P0  | Quote distance uses MapsService Valhalla (not Google)                                                       | `source=valhalla` (or labeled OSRM fallback)                            | `test_routing.py`, SPA                                      |
| MF-HS-02 | P0  | Book → Fleetbase sync enqueue                                                                               | `FleetbaseSyncJob` / retry queue; portal never hits `:8000`             | FB sync tests                                               |
| MF-HS-03 | P0  | Fleetbase status webhook → Order → notification fanout                                                      | Audience from `NOTIFICATION_AUDIENCES`; no FCM call inside adapter      | `test_fleetbase_webhook_*`, `test_notification_role_matrix` |
| MF-HS-04 | P0  | Assign / ops_critical → loud push to driver devices                                                         | Channel `ops_critical` / `assignments`; email failsafe if zero devices  | `test_notification_ops_loud_push.py`                        |
| MF-HS-05 | P0  | Live map positions from adapter REST, tiles from Google                                                     | ETA/geometry from Valhalla/OSRM/Fleetbase — not Google Directions       | `LiveMapPanel`, `validate:tracking-maps`                    |
| MF-HS-06 | P0  | Optimize → adapter orchestrator → VROOM → Valhalla                                                          | No PC VROOM client; MapsService not replaced by Google                  | `_probe_vroom`, VR catalog                                  |
| MF-HS-07 | P0  | Admin System Tests: `google_maps` + `firebase` + `valhalla` + `osrm` + `fleetbase*` + `notification_engine` | Config + live probes honest                                             | **Seeded** `test_mf_hs_open_batch.py`                       |
| MF-HS-08 | P1  | Chaos: `firebase_offline`                                                                                   | Push degrades; email path still works; strip red                        | `diagnostics_chaos` + GAP-06                                |
| MF-HS-09 | P1  | Chaos: `google_maps_failure`                                                                                | Places/tiles banner; quotes still via Valhalla                          | `_chaos_maps`                                               |
| MF-HS-10 | P1  | Chaos: `valhalla_failure` / `osrm_failure`                                                                  | Fallback or fail-closed per policy; never silent Google matrix          | FAILURE_SCENARIOS                                           |
| MF-HS-11 | P0  | Integrations matrix YAML includes `google_maps`                                                             | `pnpm validate:integrations-matrix`                                     | `REQUIRED_YAML_KEYS`                                        |
| MF-HS-12 | P0  | Graphify invariant: no firebase→fleetbase edge                                                              | After folder-graph change, re-`path` undirected only via Order/EventBus | **Seeded** `test_mf_hs12_*` + portal SC ban                 |

---

## 4. Google Maps (Places + tiles only) — `GMAP-*`

### 4.1 Package & config

| ID      | P   | Case                                                                        | Expected                                               | Files                                                                 |
| ------- | --- | --------------------------------------------------------------------------- | ------------------------------------------------------ | --------------------------------------------------------------------- |
| GMAP-01 | P0  | `isGoogleMapsConfigured` false → banner, no crash                           | `MapsMissingBanner` / degrade                          | `packages/maps`, portal `lib/env.ts`                                  |
| GMAP-02 | P0  | `AddressAutocompleteInput` GTA bias                                         | Suggestions biased to GTA bounds                       | `packages/maps/src/AddressAutocompleteInput.tsx`, `GTA_LOCATION_BIAS` |
| GMAP-03 | P0  | `GoogleMapsProvider` loads once per portal                                  | No double-script                                       | admin/merchant/customer providers                                     |
| GMAP-04 | P0  | `TrackRouteMap` / `OrderRouteMap` / `LiveMapPanel` render tiles             | Markers from API; polyline decode shared               | Ripwire maps lens                                                     |
| GMAP-05 | P0  | `_probe_google_maps` config vs live                                         | Catalog id `google_maps`                               | `diagnostics_probes`                                                  |
| GMAP-06 | P0  | **Negative:** no Distance Matrix / Directions / Roads for price or dispatch | CI vendor leaves / spatial ban                         | `verify_no_ops_spatial_math`, ARCH                                    |
| GMAP-07 | P1  | Website GBP link only (not routing)                                         | Contact/integrations                                   | `GoogleBusinessProfileLink.tsx`                                       |
| GMAP-08 | P1  | `validate:tracking-maps` REQUIRED symbols present                           | `TrackRouteMap`, `GoogleMapsProvider`, `TrackEtaPanel` | `scripts/verify_tracking_maps.py`                                     |
| GMAP-09 | P2  | Polyline encoding google vs valhalla                                        | Shared `packages/maps/src/polyline.ts`                 | clone collapse GAP-05                                                 |

### 4.2 Page / file matrix (every surface that touches Google)

| Portal        | Route / file                          | Case IDs    | Must cover                                   |
| ------------- | ------------------------------------- | ----------- | -------------------------------------------- |
| Admin         | `/operations` → `LiveMapPanel`        | UI-GMAP-A01 | Adapter positions + Google tiles; WS not SC  |
| Admin         | `/orders/[id]` → `OrderRouteMap`      | UI-GMAP-A02 | Route from PC; tiles Google                  |
| Admin         | Order builder / customer add → Places | UI-GMAP-A03 | Autocomplete only                            |
| Admin         | Merchant locations panel              | UI-GMAP-A04 | Address entry Places                         |
| Admin         | `/settings` Integrations              | UI-GMAP-A05 | Docs + probe link; no key mint theater       |
| Merchant      | `/book` `BookDeliveryClient`          | UI-GMAP-M01 | Places + Valhalla quote                      |
| Merchant      | `/track` `TrackingMap`                | UI-GMAP-M02 | Tiles + geofence circles (display)           |
| Merchant      | `/routes` `RouteModuleForm`           | UI-GMAP-M03 | Address UX                                   |
| Merchant      | `/settings` locations                 | UI-GMAP-M04 | Places                                       |
| Customer      | `/book`                               | UI-GMAP-C01 | Places                                       |
| Customer      | `/track/[trackingNumber]`             | UI-GMAP-C02 | Live track map                               |
| Driver web    | `/navigation`                         | UI-GMAP-D01 | Session from NavigationService; tiles Google |
| Driver mobile | `maps.ts` turn-by-turn                | UI-GMAP-D02 | Opens external nav app; PC ETA not Google    |
| Website       | `/track/[tracking]`                   | UI-GMAP-W01 | Public track tiles                           |

**Negative per page:** browser network tab never shows Google Distance Matrix; never Fleetbase `:8000`.

---

## 5. Spatial lane (Valhalla / OSRM) — `SPA-*` (cross-link)

Full depth: [ROUTE_OPTIMIZATION_DEV_TEST_CASES.md](ROUTE_OPTIMIZATION_DEV_TEST_CASES.md) + SYSTEM_INTEGRATIONS SPA-001+.

Must-pass for this slice:

| ID       | P   | Case                                                    | Expected                   |
| -------- | --- | ------------------------------------------------------- | -------------------------- |
| SPA-V-01 | P0  | `route` / `route_with_source` / `route_distance_meters` | Public MapsService only    |
| SPA-V-02 | P0  | `matrix_durations` for CT scoring                       | No haversine in ops        |
| SPA-V-03 | P0  | Valhalla down → local OSRM                              | Labeled source             |
| SPA-V-04 | P0  | Public demo OSRM default off                            | CI fail if unlabeled       |
| SPA-V-05 | P0  | Costing box→truck / van→auto                            | `test_valhalla_costing.py` |
| SPA-V-06 | P0  | VROOM only via Fleetbase orchestrator                   | `_probe_vroom`             |

---

## 6. Firebase FCM — `FCM-*`

| ID     | P   | Case                                                         | Expected                               | Seed                                    |
| ------ | --- | ------------------------------------------------------------ | -------------------------------------- | --------------------------------------- |
| FCM-01 | P0  | `firebase_credentials_configured` / `firebase_sdk_available` | Probe `firebase`                       | `_probe_firebase`                       |
| FCM-02 | P0  | `firebase_production_ready` false in local without keys      | Honest degrade; no crash               | `fcm_service.py`                        |
| FCM-03 | P0  | `is_fcm_registration_token` rejects Expo/APNs/`web-*` fake   | `InvalidFcmToken` → HTTP 400           | DeviceService                           |
| FCM-04 | P0  | Send when unconfigured                                       | Soft-fail / logged; no exception storm | `test_fcm_send_unconfigured`            |
| FCM-05 | P1  | Send accepts priority kwargs (loud)                          | Critical path                          | `test_fcm_send_accepts_priority_kwargs` |
| FCM-06 | P1  | Invalid token → device invalidate                            | Token pruned                           | DeviceService.invalidate                |
| FCM-07 | P0  | Firebase **Auth** never used for login                       | Clerk / Staff IdP only                 | intentional skip AUTH                   |
| FCM-08 | P1  | Mobile `google-services.json` / plist present in shells      | Documented; CI smoke                   | mobile apps                             |
| FCM-09 | P1  | Admin `firebase-messaging-sw.js` served                      | SW registers under `/`                 | `apps/admin/public/`                    |
| FCM-10 | P2  | `send_test_push.py` script                                   | Dev-only path works with flag          | `apps/api/scripts/send_test_push.py`    |

---

## 7. Push registration / revoke — `PUSH-*`

### 7.1 API

| ID      | P   | Case                         | Expected                       | Endpoint / symbol                                     |
| ------- | --- | ---------------------------- | ------------------------------ | ----------------------------------------------------- |
| PUSH-01 | P0  | Register valid FCM token     | `{device_id, registered:true}` | `POST /v1/notifications/devices/register`             |
| PUSH-02 | P0  | Register invalid token       | 400 `fcm_token_invalid`        | `register_device`                                     |
| PUSH-03 | P0  | Revoke device                | inactive                       | notifications router revoke                           |
| PUSH-04 | P0  | Driver register push         | Driver context                 | `POST` driver `register_push` / `PushRegisterRequest` |
| PUSH-05 | P0  | Driver unregister            | Cleared                        | `unregister_push`                                     |
| PUSH-06 | P1  | Max devices per user trim    | `MAX_DEVICES_PER_USER`         | DeviceService._trim_devices                           |
| PUSH-07 | P1  | Migrate legacy driver tokens | Idempotent                     | DeviceService.migrate_legacy_*                        |
| PUSH-08 | P1  | Permission string stored     | `notification_permission`      | schema                                                |

### 7.2 Clients

| ID       | P   | Case                                          | Expected                           | File                                                                   |
| -------- | --- | --------------------------------------------- | ---------------------------------- | ---------------------------------------------------------------------- |
| PUSH-C01 | P0  | Admin `registerBrowserPush`                   | Calls shared register API          | **Done** `e2e/push.p0.spec.ts` + `web-push.ts`                         |
| PUSH-C02 | P0  | Merchant `registerBrowserPush(orgId?)`        | Org-scoped principal               | **Done** `merchant-portal/e2e/push.p0.spec.ts`                         |
| PUSH-C03 | P1  | Driver web `registerWebPush`                  | Offline client path                | **Done** `driver-portal/e2e/push.p0.spec.ts` + `__PC_TEST_FCM_TOKEN__` |
| PUSH-C04 | P1  | Merchant `NotificationCenter.enablePush`      | UX + API                           | **Done** GAP-07 / MP-NTF-002                                           |
| PUSH-C05 | P1  | Mobile driver `collectPush` → `registerPush`  | Expo → FCM registration token only | **Done** GAP-08 / MOB-03                                               |
| PUSH-C06 | P1  | Driver-platform `PushService.register_device` | Delegates to DeviceService         | **Done** `test_driver_push_service.py`                                 |

---

## 8. Notification engine — `NE-*`

| ID    | P   | Case                                       | Expected                             | Seed                               |
| ----- | --- | ------------------------------------------ | ------------------------------------ | ---------------------------------- |
| NE-01 | P0  | Models: Device / Record / DeliveryLog      | ORM ownership in notification_engine | models.py                          |
| NE-02 | P0  | PreferenceService quiet hours              | No push in quiet window              | preference tests                   |
| NE-03 | P0  | UserSettingsService                        | Per-role settings                    | —                                  |
| NE-04 | P0  | DeliveryService email + push fanout        | Mailpit local                        | delivery + zeptomail tests         |
| NE-05 | P0  | Processor drain                            | Worker queue                         | `test_notifications_processor.py`  |
| NE-06 | P0  | Role matrix audiences                      | `NOTIFICATION_AUDIENCES`             | `test_notification_role_matrix.py` |
| NE-07 | P1  | Phase1/2/3 contracts                       | Existing phase files green           | `test_notification_phase*.py`      |
| NE-08 | P1  | Realtime inbox WS (PC, not SC)             | Admin token path                     | `test_notification_realtime.py`    |
| NE-09 | P1  | SLI metrics                                | Counters                             | `test_notification_sli_metrics.py` |
| NE-10 | P1  | Staff fanout `_admin_ids_with_active_push` | Only users with devices              | staff_fanout                       |
| NE-11 | P2  | Templates catalog                          | Admin list                           | templates.py                       |
| NE-12 | P0  | Single notification_engine                 | No second FCM/mail engine            | intentional skip                   |

---

## 9. Admin notification ops — `NA-*`

| ID    | P   | Case                                 | Expected                                                  | Route / UI                                |
| ----- | --- | ------------------------------------ | --------------------------------------------------------- | ----------------------------------------- |
| NA-01 | P0  | `push_health` payload                | creds, sdk, production_ready, device counts, critical 24h | `GET /v1/admin/notifications/push-health` |
| NA-02 | P0  | `PushHealthStrip` on `/operations`   | Mirrors API; red when firebase_offline                    | `PushHealthStrip.tsx`                     |
| NA-03 | P1  | `/notifications` inbox               | List/read/archive                                         | page + lib/notifications.ts               |
| NA-04 | P1  | Admin send_test / broadcast (RBAC)   | Superadmin/ops only                                       | notification_admin_service                |
| NA-05 | P1  | Retry failed delivery                | Status updates                                            | admin service retry                       |
| NA-06 | P1  | Entity alerts on order/merchant      | Care counts                                               | entity_alerts                             |
| NA-07 | P2  | Diagnostics AI usage / notif sandbox | Tables when flagged                                       | DiagnosticsAiUsageView                    |
| NA-08 | P1  | Account security + push permission   | Step-up unrelated to FCM Auth                             | `/account/security`                       |

---

## 10. Fleetbase ↔ notifications (indirect) — `FB-NF-*`

| ID       | P   | Case                                       | Expected                  | Seed                          |
| -------- | --- | ------------------------------------------ | ------------------------- | ----------------------------- |
| FB-NF-01 | P0  | Adapter never imports FCM                  | Boundary                  | fleetbase-adapter tests       |
| FB-NF-02 | P0  | Webhook status → translator → Order        | Then EventBus notify      | webhook + status translator   |
| FB-NF-03 | P0  | POD complete → customer/merchant notify    | Audience correct          | role matrix                   |
| FB-NF-04 | P0  | Driver reject / cancel failure scenario    | Loud ops push             | FAILURE_SCENARIOS + loud push |
| FB-NF-05 | P1  | Sync failure → ops notification not silent | Retry queue depth + alert | sync health                   |
| FB-NF-06 | P1  | GPS loss / vehicle_breakdown chaos         | Ops notify path           | CHAOS_SCENARIOS               |
| FB-NF-07 | P0  | Portals never SocketCluster for FB events  | PC WS / poll only         | vendor leaves                 |
| FB-NF-08 | P0  | `layered_architecture` probe               | No UI→Fleetbase           | DIAG                          |

---

## 11. Diagnostics / chaos / E2E — `DIAG-*` / `CHAOS-*`

### 11.1 `TEST_CATALOG` ids (Ripwire SSOT) — run each in Admin `/system-tests`

`clerk` · `stripe` · `firebase` · `google_maps` · `osrm` · `valhalla` · `vroom` · `fleetbase` · `fleetbase_adapter` · `fleetbase_console` · `email_smtp` · `mailpit` · `event_bus` · `websockets` · `redis` · `postgresql` · `readiness_probe` · `metrics_endpoint` · `worker_queue` · `notification_engine` · `pricing_engine` · `billing_engine` · `orders_engine` · `crm_engine` · `finance_engine` · `claims_engine` · `support_engine` · `layered_architecture` · `stripe_webhook` · `scheduled_jobs`

Per id: **DIAG-{id}-CFG** (config) · **DIAG-{id}-LIVE** (safe live) · **DIAG-{id}-DOWN** (fail-closed).

### 11.2 Chaos (Admin diagnostics + `CHAOS_SCENARIOS`)

| ID       | Scenario                                                             | Expected                               |
| -------- | -------------------------------------------------------------------- | -------------------------------------- |
| CHAOS-01 | `fleetbase_offline`                                                  | Sync queue grows; UI degrade; no crash |
| CHAOS-02 | `firebase_offline`                                                   | PushHealth red; email failsafe         |
| CHAOS-03 | `google_maps_failure`                                                | Places banner; Valhalla quotes OK      |
| CHAOS-04 | `osrm_failure`                                                       | Valhalla primary still OK              |
| CHAOS-05 | `valhalla_failure`                                                   | OSRM fallback or fail-closed           |
| CHAOS-06 | `clerk_offline`                                                      | Auth fail-closed                       |
| CHAOS-07 | `stripe_offline`                                                     | Pay degrade                            |
| CHAOS-08 | `websocket_failure`                                                  | Live map poll fallback                 |
| CHAOS-09 | `redis_restart` / `postgresql_restart`                               | Recovery                               |
| CHAOS-10 | `driver_reject` / `vehicle_breakdown` / `gps_loss` / `webhook_delay` | Ops + notify                           |

### 11.3 E2E notification audiences

Assert fanout for: `customer` · `merchant` · `driver` · `admin` · `operations` · `finance` · `support` (`NOTIFICATION_AUDIENCES`).

---

## 12. Email system (paired with push)

| ID      | P   | Case                              | Expected                           |
| ------- | --- | --------------------------------- | ---------------------------------- |
| MAIL-01 | P0  | Local SMTP → Mailpit              | `_probe_mailpit`                   |
| MAIL-02 | P0  | Not Mailhog                       | compose pin                        |
| MAIL-03 | P1  | ZeptoMail HTTPS prod              | `test_zeptomail_https_delivery.py` |
| MAIL-04 | P0  | Zero FCM devices → email failsafe | DeliveryService                    |
| MAIL-05 | P1  | Staff invite / onboarding email   | Mailpit capture                    |
| MAIL-06 | P1  | Invoice / COD reminders           | finance path                       |

---

## 13. Clerk / Shopify / ERP / other connections (you asked)

Cross-link only — full cases in SYSTEM_INTEGRATIONS + persona matrices.

| Area                     | Must-test with Maps/Push                                                    | Do not                           |
| ------------------------ | --------------------------------------------------------------------------- | -------------------------------- |
| Clerk                    | Token principal for `/v1/notifications/*`; portal triad                     | Firebase Auth                    |
| Staff IdP                | Admin push register uses staff session                                      | Customer Clerk bypass as product |
| Stripe                   | Pay events → notify; Checkout unbroken                                      | —                                |
| Shopify                  | Carrier rates via Pricing+Valhalla; order webhook → book → FB sync → notify | Google for rates                 |
| ERP / NetSuite / Zapier  | `ErpFulfillmentAdapter.map_fulfillment` → book → same notify chain          | Invent Woo/QB product tests      |
| OAuth / merchant-api     | Partner book → notify                                                       | —                                |
| Lead ingest              | Lead events → CRM notify                                                    | Phase3 AI SKU                    |
| EventBus                 | Envelope → notification processor                                           | —                                |
| SpiceDB                  | RBAC on admin notify send/broadcast                                         | Cache Check allows               |
| Nominatim                | Optional geocode fallback only                                              | Replace Places UX                |
| Checkr / Stripe Identity | Driver verify events → ops notify                                           | Auto-approve DriverStatus        |

---

## 14. UI/UX checklist (maps + push pages)

For **each** route in §4.2 and notification pages:

1. Unauth redirect / Clerk gate
2. Shell loads without console error
3. Missing Google key → banner (not blank crash)
4. Missing FCM → strip/banner + email still works
5. Tablet / mobile viewport (`validate:admin-tablet` where applicable)
6. A11y: map not sole status channel; strip has text
7. Copy: never claim Google ETA for dispatch

Notification pages: Admin `/notifications` · Merchant `/notifications` · Customer `/notifications` · Driver `/communications`.

---

## 15. Database / Docker / architecture negatives

| ID         | P   | Case                                                         | Expected         |
| ---------- | --- | ------------------------------------------------------------ | ---------------- |
| DB-NF-01   | P0  | `NotificationDevice` / `NotificationRecord` migrations apply | Alembic          |
| DB-NF-02   | P1  | Sandbox / AI usage notif tables when flagged                 | migration ai0x…  |
| DOC-NF-01  | P0  | Mailpit + Valhalla + OSRM + FB Valkey pins                   | no `:latest`     |
| ARCH-NF-01 | P0  | No SocketCluster in web/mobile src                           | vendor leaves    |
| ARCH-NF-02 | P0  | No Google routing for price/dispatch                         | spatial ban      |
| ARCH-NF-03 | P0  | No PC VROOM client                                           | vendor leaves    |
| ARCH-NF-04 | P0  | No second FCM/mail engine                                    | intentional skip |
| ARCH-NF-05 | P0  | Project mode immutable                                       | 403              |

---

## 16. Suggested implementation order

1. **GAP-01…04** (browser push tests + InvalidFcmToken + push_health contract).
2. **MF-HS-01…07** + **DIAG** firebase/google_maps/valhalla/osrm/fleetbase/notification_engine.
3. **FCM + PUSH API** + Mailpit failsafe.
4. **FB-NF** webhook→notify + loud assign.
5. **UI-GMAP / UI-PUSH** page matrix.
6. **CHAOS** firebase/google/valhalla/osrm.
7. P3: assert intentional skips still held.

When coding: CodeGraph for schemas → Ripwire `--callers` / `--expand` on the thin router → pytest next to existing `test_notification_*` / `test_routing.py` / adapter tests. Wire into `pnpm validate:*` where it belongs.

---

## 17. Related SSOT

- [ARCHITECTURE.md](../ARCHITECTURE.md) — Branch identity/push + spatial
- [INTEGRATIONS.md](../INTEGRATIONS.md) · `integrations.yaml`
- [FLEETBASE_MODULES.md](../FLEETBASE_MODULES.md) — Notifications / Maps Use-Extend-Replace
- `apps/api/src/porterchain_api/admin_engine/diagnostics_catalog.py`
- `apps/api/src/porterchain_api/admin_engine/e2e_validation_catalog.py`
- `apps/admin/src/lib/diagnostics.ts` (`CHAOS_SCENARIOS`)
- `.cursor/rules/fleetbase-first-policy.mdc` · `graph-tools.mdc`
