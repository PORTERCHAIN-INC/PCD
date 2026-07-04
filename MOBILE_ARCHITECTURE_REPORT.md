# Mobile Architecture Report

**Audit date:** June 30, 2026  
**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Supersedes:** Stale sections of [MOBILE_ARCHITECTURE.md](./MOBILE_ARCHITECTURE.md) (still marked "scaffold" — apps are fully wired)

---

## 1. Locked topology

```
┌─────────────────────┐     ┌──────────────────────┐
│  mobile-driver      │     │  mobile-customer     │
│  Expo SDK 52        │     │  Expo SDK 52         │
└──────────┬──────────┘     └──────────┬───────────┘
           │  HTTPS / WSS              │
           ▼                           ▼
┌──────────────────────────────────────────────────┐
│  Porterchain API (:8001)                         │
│  • /driver-api/v1/*  (driver)                    │
│  • /v1/*             (customer)                  │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
            Application Services (*_engine/)
                       │
                       ▼
            Fleetbase Adapter → Fleetbase (:8000)
```

**Compliance:** No mobile code calls Fleetbase, Stripe SDK, or merchant/admin APIs directly.

---

## 2. Repository layout

```
apps/
├── mobile-driver/          # @porterchain/mobile-driver
└── mobile-customer/        # @porterchain/mobile-customer

shared/
├── api/                    # @porterchain/mobile-api
├── theme/                  # @porterchain/mobile-theme
├── hooks/                  # @porterchain/mobile-hooks
├── storage/                # @porterchain/mobile-storage
├── maps/                   # @porterchain/mobile-maps
├── notifications/          # @porterchain/mobile-notifications
├── offline/                # @porterchain/mobile-offline
├── mobile-security/        # @porterchain/mobile-security
├── mobile-performance/     # @porterchain/mobile-performance
├── components/             # @porterchain/mobile-components
└── mobile-ui/              # @porterchain/mobile-ui
```

---

## 3. Provider tree (both apps)

```
SafeAreaProvider
└── ThemeProvider
    └── QueryClientProvider
        └── PerformanceProvider          # focus manager, metrics
            └── MapsProvider
                └── MobileUiProvider
                    └── ToastProvider
                        └── SecurityLayer    # ClerkBridge → MobileSecurityProvider
                            └── ApiProvider  # createSecureApiClient
                                └── OfflineSyncLayer
                                    └── NotificationLayer
                                        └── RootNavigator
```

---

## 4. Navigation architecture

### Driver (6 tabs)

| Tab | Stack | Key screens |
|-----|-------|-------------|
| Home | HomeStack | Dashboard |
| Jobs | JobsStack | Jobs, JobDetail, AssignmentQueue, Pod†, Incident† |
| Navigation | NavigationStack | Navigation†, LiveMap |
| Earnings | EarningsStack | Earnings |
| Shift | ShiftStack | Shift |
| More | MoreStack | Profile, Notifications, OfflineSync†, Support, SOS†, Settings, Performance† |

† = lazy-loaded via `createLazyScreen` (`@porterchain/mobile-performance`)

### Customer (5 tabs)

| Tab | Stack | Key screens |
|-----|-------|-------------|
| Home | HomeStack | Dashboard |
| Bookings | BookingsStack | Bookings, Quote, Booking, Draft, StripeCheckout†, Confirmation |
| Tracking | TrackingStack | Tracking, LiveMap†, History |
| Notifications | NotificationsStack | NotificationCenter |
| Profile | ProfileStack | Profile, Invoices, Receipts, Support, Claims†, OfflineSync†, Settings, Performance† |

### Deep linking

| Mechanism | Implementation |
|-----------|----------------|
| Custom scheme | `porterchain-driver://`, `porterchain-customer://` |
| Push tap (warm) | `NotificationProvider` → `onDeepLink` |
| Push tap (cold) | `getInitialNotification` + `onNotificationOpenedApp` |
| URL cold start | `useAppLinking` + `expo-linking` |
| React Navigation `linking` config | Not configured (custom handlers used) |

**Driver routes:** `jobs/{id}`, `navigation`, `support`, `sos`, `notifications`  
**Customer routes:** `tracking/{id}`, `bookings`, `support`, `claims`, `notifications`

---

## 5. API boundaries

### Driver → `/driver-api/v1`

| Domain | Client method | Server |
|--------|---------------|--------|
| Auth | `login`, `refreshSession` | `driver_engine/auth_service` |
| Jobs / routes | `jobs`, `job`, `acceptOrder`, `rejectOrder` | `porterchain_driver` |
| POD | `podPhoto`, `podSignature`, `podComplete`, `generateOtp` | `driver_engine` + Fleetbase bridge |
| GPS | `postLocation` | → Fleetbase adapter |
| Shift | `shiftStart`, `shiftEnd`, `setAvailability` | `porterchain_driver` |
| Offline | `queueOffline`, `syncOffline` | `porterchain_driver/offline` |
| Push | `registerPush` | `notification_engine` |

### Customer → `/v1`

| Domain | Client method | Server |
|--------|---------------|--------|
| Auth | `authMe` (Clerk bearer) | `auth/principal_resolver` |
| Bookings | `createQuote`, `startBooking`, `getBookingConfirmation` | `booking_engine` |
| Tracking | `getOrder`, `getLiveTracking` | `booking_engine` + Fleetbase tracking |
| Billing | dashboard `invoices`, `payments` | `merchant_engine` / billing |
| Notifications | inbox, prefs, device register | `notification_engine` |

---

## 6. Offline architecture

```
Screen action
    ↓
runDirectOrQueue (online → API, offline → MMKV queue)
    ↓
OfflineSyncProvider (30s driver / 45s customer, paused in background)
    ↓
POST /driver-api/v1/offline/sync → offline_executor → Application Services
    ↓
Fleetbase Adapter (when execution required)
```

| App | Queue | Server sync | Background GPS |
|-----|-------|---------------|----------------|
| Driver | MMKV enterprise queue | ✅ Full | ✅ `expo-task-manager` |
| Customer | MMKV local | ❌ Stub adapter | N/A |

---

## 7. Notifications architecture

```
FCM (native) ──┐
               ├──► NotificationProvider ──► React Query inbox cache
WebSocket ─────┘         │
                         ├── Badge sync
                         └── Deep link → navigation
```

- **Engine:** Notification Engine only — mobile never sends push directly.
- **Realtime:** `WS /v1/notifications/ws` with exponential backoff; paused in background.
- **FCM:** Foreground merge into inbox; device register on sign-in.

---

## 8. Maps & Fleetbase (display-only)

- `EnterpriseMap` renders server-provided polylines, driver position, geofences.
- GPS source labeled `fleetbase` from API — mobile does not compute routes.
- Driver navigation opens external Google Maps URL from `navigation_url`.

---

## 9. Payments (customer)

- Hosted Stripe Checkout URL from `startBooking`.
- Confirmation via polling `getBookingConfirmation` (server updated by Stripe webhook).
- No Stripe RN SDK — compliant with masterrule §14.

---

## 10. Architecture gaps

| Gap | Severity | Recommendation |
|-----|----------|----------------|
| `MOBILE_ARCHITECTURE.md` outdated | Low | Update scaffold status |
| Customer not in masterrule §4.1 repo tree | Low | Add to masterrule |
| Guest tracking behind auth | Medium | Optional auth stack for public tracking |
| Driver upload stub | High | Presigned upload API |
| Customer offline sync stub | Medium | Mirror driver offline endpoints or document support-only |
| Universal links | Medium | `associatedDomains` + Navigation linking config |

---

## 11. Related documents

- [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md)
- [MOBILE_SECURITY_REPORT.md](./MOBILE_SECURITY_REPORT.md)
- [FLEETBASE_INTEGRATION.md](./FLEETBASE_INTEGRATION.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
