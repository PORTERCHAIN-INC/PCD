# Driver Platform — Integration Matrix

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Scope:** driver web portal, mobile driver app, `/driver-api/v1/*`, Fleetbase adapter, notification engine

Legend: ✅ Integrated · ⚠ Partial · ❌ Missing · — Not applicable

---

## Client → Porterchain API

| Capability | Web Portal | Mobile Driver | API / Service | Status |
| ---------- | ---------- | ------------- | ------------- | ------ |
| Clerk login → Porterchain JWT | `/api/auth/login` | `SignInScreen` | `POST /driver-api/v1/auth/login` | ✅ |
| Refresh token | Cookie present, BFF route missing | `createSecureApiClient` refresh callback | `POST /driver-api/v1/auth/refresh` | ⚠ web / ✅ mobile |
| Session guard | `middleware.ts` | secure auth store | `require_approved_driver` | ✅ |
| Dashboard | `/` | Home tab | `DashboardService` | ✅ |
| Jobs list/detail | `/jobs`, `/jobs/[orderId]` | Jobs stack | `JobsService` | ✅ |
| Accept/reject | Job detail | Jobs/detail | `AvailabilityService` | ✅ |
| Assigned route/stops | Jobs/navigation | Jobs + POD screens | `StopsService` | ✅ |
| Start route | API client / workflow | API client | `StopsService` | ⚠ UI-dependent |
| Arrive/deliver/exception | Job detail | Jobs/POD/Incident screens | `StopsService` | ✅ |
| POD photo/signature/complete | Job detail | `PodScreen` | `ProofOfDeliveryService` | ✅ |
| Generate/verify OTP | Job detail | `PodScreen` | `ProofOfDeliveryService` | ✅ |
| Navigation session | `/navigation` | Navigation tab | `NavigationService` | ✅ |
| Location ping | Navigation/location flows | `expo-location` service | `LocationService` | ✅ |
| Shift lifecycle | `/shift` | Shift tab | `ShiftService` | ✅ |
| Availability | Shift controls | Shift controls | `AvailabilityService` | ✅ |
| Earnings/wallet | `/earnings`, `/wallet` | Earnings tab | `FinanceService` / `EarningsService` | ✅ |
| Profile/onboarding | `/profile` | Profile screen | `ProfileService` | ✅ |
| Documents/vehicle | Profile | Profile flows | Profile/doc services | ⚠ partial UX |
| Support tickets | `/support` | Support screen | `SupportService` | ✅ |
| Claims/incidents | Support/job detail | Incident screen | Support/incident services | ✅ |
| Emergency/SOS | `/emergency` | SOS screen | `EmergencyService` | ✅ |
| Communications inbox | `/communications` | Notifications screen | `DriverCommunicationService` | ✅ |
| Mark/archive/read notifications | Communications | Notifications screen | Notification engine | ✅ |
| Push registration | Profile/settings | FCM register | `PushService` → `DeviceService` | ✅ mobile / ⚠ web |
| Offline queue | offline client | MMKV offline provider | `OfflineService` | ✅ |
| Offline sync/retry | BFF proxy | 30s auto-sync | `offline_executor` | ✅ |
| Performance diagnostics | portal pages | Performance screen | client diagnostics | ✅ |

**Coverage:** web portal now exercises most primary driver workflows; mobile covers the execution path (jobs, POD, GPS, shift, offline, push). The remaining partial areas are web refresh UX, production web push, and a few profile/document subflows.

---

## Porterchain Services → Internal Engines

| Driver Module | Internal Engine | Purpose | Status |
| ------------- | --------------- | ------- | ------ |
| `finance.py` | `billing_engine/driver_finance_service.py` | Earnings, statements, payouts | ✅ |
| `support_bridge.py` | support/claims services | Tickets, claims, knowledge base | ✅ |
| `communications.py` | `notification_engine` | Inbox, preferences, push state | ✅ |
| `push.py` | `notification_engine/device_service.py` | FCM registration | ✅ |
| `jobs.py` | order/admin services | Timeline and job state reads | ✅ |
| `navigation.py` | maps/routing services | Route, ETA, polyline | ✅ |
| `offline.py` | `driver_engine/offline_executor.py` | Replay queued driver actions | ✅ |
| `emergency.py` | event/ops surfaces | SOS event + support visibility | ⚠ rate-limit gap |

---

## Driver Service → Fleetbase Adapter

| Driver Action | Bridge / Adapter Role | Status |
| ------------- | --------------------- | ------ |
| GPS ping | Track driver location | ✅ |
| Go online/offline | Toggle Fleetbase availability | ✅ |
| Accept order | Sync accepted state | ✅ |
| Reject order | Return to dispatch-ready state | ✅ |
| Start route / en route | Start order execution | ✅ |
| Arrive pickup/dropoff | Status sync | ✅ |
| Deliver / POD complete | Complete order execution | ✅ |
| Stop exception | Failed/exception sync | ✅ |
| POD photo/signature/barcode | Proof media upload | ✅ |
| Route polyline | Fetch route geometry | ✅ |

**Bridge gate:** `FLEETBASE_DISPATCH_BRIDGE=true` and adapter enabled. Clients never call Fleetbase directly.

---

## Event Bus → Notification Engine → Driver

| Domain Event | Driver Outcome | Channel | Status |
| ------------ | -------------- | ------- | ------ |
| `order.driver_accepted` / `order.driver_rejected` | Assignment state update | in-app | ✅ |
| `driver.route_changed` | Route update | push + in-app | ✅ |
| `driver.emergency` | Ops alert | in-app/admin | ✅ |
| `incident.reported` | Incident logged | in-app | ✅ |
| `driver.shift_started` / `driver.shift_ended` | Shift activity | in-app | ✅ |
| support/claim events | Support status | push + in-app | ✅ |
| Fleetbase webhook events | Customer/ops tracking | notification/event bridge | ✅ |

---

## Offline Executor → Services

| Action Type | Delegate | Fleetbase on Sync | Status |
| ----------- | -------- | ----------------- | ------ |
| `location` | `location.record_ping` | ✅ | ✅ |
| `arrive_stop` | `stops.arrive_stop` | ✅ | ✅ |
| `deliver_stop` | `stops.deliver_stop` | ✅ | ✅ |
| `pod_photo` / `camera_upload` | `pod.capture_photo` | ✅ | ✅ |
| `pod_signature` | `pod.capture_signature` | ✅ | ✅ |
| `pod_barcode` | `pod.capture_barcode` | ✅ | ✅ |
| `pod_complete` | `pod.complete_pod` | ✅ | ✅ |
| `availability` | availability/shift services | ✅ | ✅ |
| `shift_*` | `shift.*` | ⚠ when applicable | ✅ |
| `document_upload` | documents/profile services | — | ⚠ UX partial |
| `incident` | `incidents.report_incident` | — | ✅ |
| `support_ticket` | `support.create_ticket` | — | ✅ |

---

## External Systems

| System | Driver Access | Integration Path | Status |
| ------ | ------------- | ---------------- | ------ |
| Fleetbase | ❌ Never direct | API → adapter/bridge | ✅ |
| Clerk | ✅ Auth only | Clerk token → Porterchain JWT | ✅ |
| Google Maps | ✅ Display/maps SDK | API provides route truth; client renders map | ✅ |
| Firebase FCM | ✅ Mobile native | `DeviceService` registration | ✅ mobile / ⚠ web |
| Stripe | ❌ Not driver scope | billing engine only | — |
| PostgreSQL 16 | ❌ No client access | API/services only | ✅ |

---

## Integration Health Summary

| Integration | Health |
| ----------- | ------ |
| Web UI → BFF → Driver API | ✅ Healthy |
| Mobile → Driver API | ✅ Healthy |
| Driver API → `porterchain_driver` services | ✅ Healthy |
| Driver services → Fleetbase adapter | ✅ Healthy, needs latency metrics |
| Driver services → notification engine | ✅ Healthy |
| Offline queue → executor | ✅ Healthy |
| WebSocket notifications | ⚠ Works, token-in-query remains a security concern |
| Firebase mobile push | ✅ Wired; production credentials required |
| Web push | ⚠ Synthetic token path / production policy open |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md) | Driver platform architecture |
| [DRIVER_PERFORMANCE_REPORT.md](./DRIVER_PERFORMANCE_REPORT.md) | Performance and scale risks |
| [DRIVER_SECURITY_REPORT.md](./DRIVER_SECURITY_REPORT.md) | Driver security findings |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md) | Mobile stack details |
