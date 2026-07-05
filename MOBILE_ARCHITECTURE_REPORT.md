# Mobile Architecture Report


**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [MOBILE_ARCHITECTURE.md](MOBILE_ARCHITECTURE.md) (canonical doc).

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Canonical for:** [MOBILE_ARCHITECTURE.md](./MOBILE_ARCHITECTURE.md)

---

## Locked Topology

```
mobile-driver (Expo SDK 52)       mobile-customer (Expo SDK 52)
        │                                      │
        │ HTTPS / WSS                          │ HTTPS / WSS
        ▼                                      ▼
Porterchain API :8001                  Porterchain API :8001
  /driver-api/v1/*                       /v1/*
        │                                      │
        ├──────────── Application services (*_engine/) ────────────┐
        │                                                          │
        ▼                                                          ▼
PostgreSQL 16                                           Fleetbase adapter
                                                               │
                                                               ▼
                                                        Fleetbase :8000
```

**Compliance:** mobile apps never call Fleetbase, merchant API, admin API, or Stripe native SDK directly. Stripe is hosted checkout through Porterchain server responses.

---

## Repository Layout

```
apps/
├── mobile-driver/          # @porterchain/mobile-driver
└── mobile-customer/        # @porterchain/mobile-customer

shared/
├── api/                    # @porterchain/mobile-api
├── components/             # @porterchain/mobile-components
├── hooks/                  # @porterchain/mobile-hooks
├── maps/                   # @porterchain/mobile-maps
├── mobile-performance/     # @porterchain/mobile-performance
├── mobile-security/        # @porterchain/mobile-security
├── mobile-ui/              # @porterchain/mobile-ui
├── notifications/          # @porterchain/mobile-notifications
├── offline/                # @porterchain/mobile-offline
├── storage/                # @porterchain/mobile-storage
└── theme/                  # @porterchain/mobile-theme
```

---

## Provider Tree

Both apps share the same provider shape:

```
SafeAreaProvider
└── ThemeProvider
    └── QueryClientProvider
        └── PerformanceLayer
            └── MapsProvider
                └── MobileUiProvider
                    └── ToastProvider
                        └── SecurityLayer
                            └── ApiProvider
                                └── OfflineSyncLayer
                                    └── NotificationLayer
                                        └── RootNavigator
```

Driver uses `DriverApiProvider`; customer uses `CustomerApiProvider`. Both wrap `createSecureApiClient`.

---

## Navigation Architecture

### Driver App

| Tab | Stack | Key Screens |
| --- | ----- | ----------- |
| Home | HomeStack | Dashboard |
| Jobs | JobsStack | Jobs, JobDetail, AssignmentQueue, POD, Incident |
| Navigation | NavigationStack | Navigation, live map |
| Earnings | EarningsStack | Earnings |
| Shift | ShiftStack | Shift |
| More | MoreStack | Profile, Notifications, OfflineSync, Support, SOS, Settings, Performance |

### Customer App

| Tab | Stack | Key Screens |
| --- | ----- | ----------- |
| Home | HomeStack | Dashboard |
| Bookings | BookingsStack | Bookings, Quote, Booking, Draft, StripeCheckout, Confirmation |
| Tracking | TrackingStack | Tracking, LiveMap, History |
| Notifications | NotificationsStack | Notification center |
| Profile | ProfileStack | Profile, Invoices, Receipts, Support, Claims, OfflineSync, Settings, Performance |

### Deep Linking

| Mechanism | Implementation |
| --------- | -------------- |
| Custom schemes | `porterchain-driver://`, `porterchain-customer://` |
| Push tap | `NotificationProvider` → app-specific deep-link handler |
| Cold-start push | FCM initial notification handlers |
| URL cold start | `useAppLinking` + `expo-linking` |
| Universal links | ⚠ Not configured |

---

## API Boundaries

### Driver → `/driver-api/v1`

| Domain | Client Methods | Server |
| ------ | -------------- | ------ |
| Auth | `login`, `refreshSession` | `driver_engine/auth_service` |
| Dashboard/jobs/routes | `dashboard`, `jobs`, `job`, `route` | `porterchain_driver` |
| Execution | `acceptOrder`, `rejectOrder`, `arriveStop`, `deliverStop`, `stopException` | `StopsService` / bridge |
| POD | `podPhoto`, `podSignature`, `podComplete`, `generateOtp` | POD service + Fleetbase adapter |
| GPS | `postLocation` | `LocationService` → Fleetbase track |
| Shift | `shiftStart`, `shiftEnd`, `shiftBreak`, `setAvailability` | `ShiftService` / availability |
| Offline | `queueOffline`, `offlinePending`, `syncOffline`, `retryOffline` | offline executor |
| Push | `registerPush` | notification `DeviceService` |

### Customer → `/v1`

| Domain | Client Methods | Server |
| ------ | -------------- | ------ |
| Auth | `authMe` | Clerk principal resolver |
| Dashboard | `dashboard` | customer/dashboard services |
| Quote/booking | `createQuote`, `startBooking`, draft methods | booking engine |
| Payment | `retryPayment`, hosted checkout flow | billing/Stripe webhook path |
| Tracking | `getOrder`, `getLiveTracking` | booking/tracking + Fleetbase adapter |
| Support | `listSupport`, `createSupport` | customer support services |
| Notifications | inbox/history/read/archive/preferences | notification engine |
| Push | `registerPushDevice` | notification `DeviceService` |

---

## Offline Architecture

```
Screen action
    ↓
run direct when online, or enqueue in MMKV
    ↓
OfflineSyncProvider
    ↓
Driver: POST /driver-api/v1/offline/* → offline_executor
Customer: local/stub adapter until server reconciliation is added
```

| App | Queue | Auto Sync | Server Sync | Notes |
| --- | ----- | --------- | ----------- | ----- |
| Driver | MMKV enterprise queue | 30s | ✅ Full driver executor | Background GPS enabled |
| Customer | MMKV local queue | 45s | ⚠ Stub/local | Needs server-backed reconciliation |

---

## Notifications Architecture

```
FCM native token
    ↓
NotificationProvider
    ├── register device with Porterchain API
    ├── merge foreground events into inbox cache
    └── deep link into navigation

WebSocket /v1/notifications/ws
    ↓
Realtime inbox/badge updates with polling fallback
```

| Feature | Driver | Customer |
| ------- | ------ | -------- |
| FCM token registration | ✅ `/driver-api/v1/push/register` | ✅ `/v1/notifications/devices/register` |
| Inbox/history/read/archive | ✅ | ✅ |
| Preferences | ✅ via notification API | ✅ |
| Deep links | ✅ | ✅ |
| Universal links | ⚠ | ⚠ |

---

## Maps And Fleetbase

| Concern | Driver | Customer |
| ------- | ------ | -------- |
| Map rendering | `EnterpriseMap`, navigation screen | tracking/live map screens |
| Route truth | Porterchain API / Fleetbase adapter | Porterchain API / Fleetbase adapter |
| GPS writes | Driver app posts `/location` | N/A |
| Direct Fleetbase access | ❌ | ❌ |
| Google Maps key | `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | same |

---

## Security Architecture

| Layer | Implementation | Status |
| ----- | -------------- | ------ |
| Clerk | `@clerk/clerk-expo`, `ClerkSignInPanel` | ✅ |
| API client | `createSecureApiClient` | ✅ |
| Driver refresh | `/driver-api/v1/auth/refresh` callback | ✅ |
| Secure storage | Secure Store / mobile auth stores | ✅ |
| PIN/biometric shell | `@porterchain/mobile-security` | ✅ |
| Security audit events | `emitSecurityEvent` | ✅ |
| Certificate pinning | package support, not enforced | ⚠ |
| Dev bypass | allowed only for local/dev configs | ⚠ production guard required |

---

## Release Architecture

| Item | Driver | Customer |
| ---- | ------ | -------- |
| Expo SDK | 52 | 52 |
| React Native | 0.76.3 | 0.76.3 |
| EAS config | ✅ | ✅ |
| Dev port | 8081 default | 8082 |
| Bundle/package ids | ✅ | ✅ |
| Firebase native paths | ✅ | ✅ |
| Store assets | ✅ | ⚠ incomplete |
| `EAS_PROJECT_ID` | fixed in app config | env-dependent |

---

## Known Architecture Gaps

| Gap | Severity | Recommendation |
| --- | -------- | -------------- |
| Customer server offline sync is stub/local | Medium | Add `/v1/offline/*` or document local-only behavior |
| Customer store assets incomplete | High | Add icon/splash/adaptive assets before release |
| Universal links absent | Medium | Add iOS associated domains and Android intent filters |
| Crash reporting absent | Medium | Add Sentry or equivalent |
| Certificate pinning not enforced | Low/Medium | Enable after production API host and pins stabilize |
| Driver POD upload hardening | High | Use production presigned upload flow |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md) | Release readiness, security, and performance |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md) | Driver integration coverage |
| [CONNECTIONS.md](./CONNECTIONS.md) | Mobile/API contracts |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
