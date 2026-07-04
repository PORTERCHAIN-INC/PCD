# Driver Platform — Integration Matrix

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Date:** June 30, 2026

Legend: ✅ Integrated · ⚠ Partial · ❌ Missing · — Not applicable

---

## 1. Client → Porterchain API

| UI Module                    | BFF Path                                | API Endpoint                     | Service                      | UI Wired        |
| ---------------------------- | --------------------------------------- | -------------------------------- | ---------------------------- | --------------- |
| Auth                         | `/api/auth/login`                       | `POST /driver-api/v1/auth/login` | `DriverAuthService`          | ✅              |
| Session                      | `/api/auth/session`                     | Cookie check                     | —                            | ✅              |
| WS token                     | `/api/auth/ws-token`                    | Cookie → bearer                  | —                            | ✅              |
| Dashboard                    | `/api/driver/v1/dashboard`              | `GET /dashboard`                 | `DashboardService`           | ✅              |
| Me                           | `/api/driver/v1/me`                     | `GET /me`                        | `ProfileService`             | ✅              |
| Jobs list                    | `/api/driver/v1/jobs`                   | `GET /jobs`                      | `JobsService`                | ✅              |
| Job detail                   | `/api/driver/v1/jobs/{id}`              | `GET /jobs/{id}`                 | `JobsService`                | ✅              |
| Job history                  | `/api/driver/v1/jobs/history`           | `GET /jobs/history`              | `JobsService`                | ✅              |
| Accept job                   | `/api/driver/v1/orders/{id}/accept`     | `POST /orders/{id}/accept`       | `AvailabilityService`        | ✅              |
| Reject job                   | `/api/driver/v1/orders/{id}/reject`     | `POST /orders/{id}/reject`       | `AvailabilityService`        | ✅              |
| Assigned route               | `/api/driver/v1/routes/assigned`        | `GET /routes/assigned`           | `StopsService`               | ✅              |
| Route stops                  | `/api/driver/v1/routes/{id}/stops`      | `GET /routes/{id}/stops`         | `StopsService`               | ✅              |
| Start route                  | `/api/driver/v1/routes/{id}/start`      | `POST /routes/{id}/start`        | `StopsService`               | ⚠ API only      |
| Arrive stop                  | `.../stops/{id}/arrive`                 | `POST`                           | `StopsService`               | ✅ Delivery 360 |
| Deliver stop                 | `.../stops/{id}/deliver`                | `POST`                           | `StopsService`               | ✅ Delivery 360 |
| Stop exception               | `.../stops/{id}/exception`              | `POST`                           | `StopsService`               | ✅ Delivery 360 |
| POD photo                    | `.../pod-photo`                         | `POST`                           | `ProofOfDeliveryService`     | ✅              |
| POD signature                | `.../pod-signature`                     | `POST`                           | `ProofOfDeliveryService`     | ✅              |
| POD complete                 | `.../pod-complete`                      | `POST`                           | `ProofOfDeliveryService`     | ✅              |
| Generate OTP                 | `/api/driver/v1/orders/{id}/otp`        | `POST`                           | `ProofOfDeliveryService`     | ✅              |
| Navigation session           | `/api/driver/v1/navigation/session`     | `GET`                            | `NavigationService`          | ✅              |
| Navigation route             | `/api/driver/v1/navigation/route`       | `GET`                            | `NavigationService`          | ⚠ API only      |
| Job navigation               | `/api/driver/v1/orders/{id}/navigation` | `GET`                            | `NavigationService`          | ⚠ API only      |
| Location ping                | `/api/driver/v1/location`               | `POST`                           | `LocationService`            | ✅              |
| Shift snapshot               | `/api/driver/v1/shift`                  | `GET`                            | `ShiftService`               | ✅              |
| Shift start/end/break/resume | `/api/driver/v1/shift/*`                | `POST`                           | `ShiftService`               | ✅              |
| Availability                 | `/api/driver/v1/availability`           | `POST`                           | `ShiftService`               | ✅              |
| Earnings                     | `/api/driver/v1/earnings`               | `GET`                            | `FinanceService`             | ✅              |
| Earnings today               | `/api/driver/v1/earnings/today`         | `GET`                            | `EarningsService`            | ⚠ API only      |
| Statements                   | `/api/driver/v1/earnings/statements`    | `GET`                            | `FinanceService`             | ✅              |
| Wallet                       | `/api/driver/v1/wallet`                 | `GET`                            | `WalletService`              | ✅              |
| Bonuses                      | `/api/driver/v1/bonuses`                | `GET`                            | `BonusesService`             | ⚠ API only      |
| Profile                      | `/api/driver/v1/profile`                | `GET`                            | `ProfileService`             | ✅              |
| Documents                    | `/api/driver/v1/documents`              | `GET/POST`                       | `DocumentsService`           | ✅              |
| Vehicle                      | `/api/driver/v1/vehicle`                | `GET`                            | `VehicleService`             | ✅              |
| Vehicle photos               | `/api/driver/v1/profile/vehicle-photos` | `POST`                           | `ProfileService`             | ✅              |
| Insurance                    | `/api/driver/v1/insurance`              | `GET`                            | `InsuranceService`           | ✅ (redirect)   |
| Training                     | `/api/driver/v1/training`               | `GET`                            | `TrainingService`            | ✅              |
| Support hub                  | `/api/driver/v1/support/hub`            | `GET`                            | `SupportBridgeService`       | ✅              |
| Create ticket                | `/api/driver/v1/support`                | `POST`                           | `SupportService`             | ✅              |
| Open claim                   | `/api/driver/v1/support/claims`         | `POST`                           | `SupportBridgeService`       | ✅              |
| Incidents                    | `/api/driver/v1/incidents`              | `GET/POST`                       | `IncidentsService`           | ✅              |
| Emergency                    | `/api/driver/v1/emergency`              | `POST`                           | `EmergencyService`           | ✅              |
| Communications hub           | `/api/driver/v1/communications`         | `GET`                            | `DriverCommunicationService` | ✅              |
| Mark notification read       | `.../notifications/{id}/read`           | `POST`                           | `DriverCommunicationService` | ✅              |
| Push register                | `/api/driver/v1/push/register`          | `POST`                           | `PushService`                | ✅              |
| Offline queue                | `/api/driver/v1/offline/queue`          | `POST`                           | `OfflineService`             | ✅              |
| Offline sync                 | `/api/driver/v1/offline/sync`           | `POST`                           | `OfflineService`             | ✅              |
| Offline retry                | `.../communications/offline/retry`      | `POST`                           | `OfflineService`             | ✅              |
| Performance                  | `/api/driver/v1/performance`            | `GET`                            | `PerformanceService`         | ✅              |
| Ratings                      | `/api/driver/v1/ratings`                | `GET`                            | `RatingsService`             | ✅              |

**Coverage:** ~55 BFF methods / ~68 API endpoints ≈ **81% UI wiring**.

---

## 2. Porterchain Service → Internal Engines

| Driver Service       | Internal Engine                            | Purpose                       |
| -------------------- | ------------------------------------------ | ----------------------------- |
| `finance.py`         | `billing_engine/driver_finance_service.py` | Earnings, statements, payouts |
| `support_bridge.py`  | `admin_engine` Support + Claims            | Tickets, claims, KB           |
| `communications.py`  | `notification_engine`                      | Inbox, push status            |
| `push.py`            | `notification_engine/device_service.py`    | FCM registration              |
| `jobs.py` (timeline) | `admin_engine/orders_service.py`           | Order timeline read           |
| `navigation.py`      | `MapsService` (OSRM/Valhalla)              | Routing fallback              |
| `navigation.py`      | `TrackingService`                          | Live tracking read            |

---

## 3. Driver Service → Fleetbase Adapter

| Driver Action          | Bridge Method                      | Adapter Method             | Fleetbase capability |
| ---------------------- | ---------------------------------- | -------------------------- | -------------------- |
| GPS ping               | `track_driver_location`            | `track_driver_location`    | Driver location      |
| Go online/offline      | `toggle_driver_online`             | `toggle_driver_online`     | Availability         |
| Accept order           | `sync_order_state(ACCEPTED)`       | `update_order_status`      | Order accepted       |
| Reject order           | `sync_order_state(DISPATCH_READY)` | `update_order_status`      | Back to pending      |
| Start route / en route | `sync_order_state(EN_ROUTE)`       | `start_order_execution`    | Execution started    |
| Arrive pickup/dropoff  | `sync_order_state`                 | `update_order_status`      | Status update        |
| Deliver / POD complete | `sync_order_state`                 | `complete_order_execution` | Completion           |
| Stop exception         | `sync_order_state(FAILED)`         | `update_order_status`      | Failed               |
| POD photo              | `upload_pod_photo`                 | `upload_pod_photo`         | Proof media          |
| POD signature          | `upload_pod_signature`             | `upload_pod_signature`     | Proof media          |
| POD barcode            | `upload_pod_barcode`               | `upload_pod_barcode`       | Proof media          |
| Route polyline         | `fetch_route`                      | `fetch_route`              | Route geometry       |

**Bridge gate:** `settings.fleetbase_dispatch_bridge && adapter.is_enabled`

---

## 4. Event Bus → Notification Engine → Driver

| Domain Event                   | Driver notification | Channel             |
| ------------------------------ | ------------------- | ------------------- |
| `DRIVER_ASSIGNED`              | Assignment alert    | push + in_app       |
| `DRIVER_ACCEPTED`              | Confirmation        | in_app              |
| `driver.route_changed`         | Route change        | push + in_app       |
| `driver.emergency`             | Ops alert           | in_app (admin)      |
| `CLAIM_OPENED`                 | Claims update       | push + in_app       |
| `CLAIM_RESOLVED`               | Claims update       | push + in_app       |
| `SUPPORT_TICKET_CREATED`       | Support message     | push + in_app       |
| `incident.reported`            | Incident logged     | in_app              |
| `driver.shift_started/ended`   | Shift activity      | in_app              |
| `driver.break_started/resumed` | Break activity      | in_app              |
| `FLEETBASE_STATUS_UPDATED`     | Tracking (customer) | — (customer-facing) |

---

## 5. Offline executor → Services

| Action type                   | Executor delegates to       | Fleetbase on sync |
| ----------------------------- | --------------------------- | ----------------- |
| `location`                    | `location.record_ping`      | ✅                |
| `arrive_stop`                 | `stops.arrive_stop`         | ✅                |
| `deliver_stop`                | `stops.deliver_stop`        | ✅                |
| `pod_photo` / `camera_upload` | `pod.capture_photo`         | ✅                |
| `pod_signature`               | `pod.capture_signature`     | ✅                |
| `pod_barcode`                 | `pod.capture_barcode`       | ✅                |
| `pod_complete`                | `pod.complete_pod`          | ✅                |
| `availability`                | `shift` / `availability`    | ✅                |
| `shift_*`                     | `shift.*`                   | ✅                |
| `document_upload`             | `documents.upload_document` | —                 |
| `incident`                    | `incidents.report_incident` | —                 |
| `support_ticket`              | `support.create_ticket`     | —                 |

---

## 6. External systems (no direct driver access)

| System       | Driver access   | Integration path                        |
| ------------ | --------------- | --------------------------------------- |
| Fleetbase    | ❌ Never direct | Adapter via bridge                      |
| Stripe       | ❌              | Not in driver scope                     |
| Clerk        | ✅ Auth only    | Login → Porterchain JWT                 |
| Google Maps  | ✅ Client SDK   | Display only; routing via API           |
| Firebase FCM | ⚠ Server-side   | DeviceService; web uses synthetic token |

---

## 7. Mobile driver app coverage

| Module           | Mobile screen | API wired |
| ---------------- | ------------- | --------- |
| Login            | ✅            | ✅        |
| Dashboard        | ✅            | Partial   |
| Push             | ✅            | ✅        |
| Jobs / POD / Nav | ❌            | ❌        |
| Shift / Earnings | ❌            | ❌        |

Mobile is **not** integrated to the full matrix — web portal is primary.

---

## 8. Integration health summary

| Integration                              | Health                             |
| ---------------------------------------- | ---------------------------------- |
| UI → BFF → API                           | ✅ Healthy                         |
| API → porterchain_driver                 | ✅ Healthy                         |
| porterchain_driver → Fleetbase           | ✅ Healthy (accept/reject patched) |
| porterchain_driver → Finance Engine      | ✅ Healthy                         |
| porterchain_driver → Support/Claims      | ✅ Healthy                         |
| porterchain_driver → notification_engine | ✅ Healthy                         |
| Fleetbase webhooks → notifications       | ✅ Healthy (inbound)               |
| Offline queue → executor                 | ✅ Healthy                         |
| WebSocket notifications                  | ⚠ Direct API connection            |
| Firebase web push                        | ⚠ Synthetic tokens                 |
