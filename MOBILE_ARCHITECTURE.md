# Porterchain Mobile Architecture

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Date:** June 30, 2026  
**Status:** Scaffold — providers, navigation shell, shared packages configured. **No feature screens.**

---

## 1. Locked topology (mobile)

```
┌─────────────────────┐     ┌──────────────────────┐
│  mobile-driver      │     │  mobile-customer     │
│  (Expo RN)          │     │  (Expo RN)           │
└──────────┬──────────┘     └──────────┬───────────┘
           │                           │
           │  HTTPS only               │
           ▼                           ▼
┌──────────────────────────────────────────────────┐
│     Porterchain API (:8001)                      │
│     Logistics Orchestrator                       │
│  • /driver-api/v1/*  (driver app)                │
│  • /v1/*             (customer app)              │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
            Application Services (*_engine/)
                       │
                       ▼
            Fleetbase Adapter → Fleetbase (:8000)
```

**Hard rules (masterrule §2, §7):**

| Rule                          | Mobile enforcement                            |
| ----------------------------- | --------------------------------------------- |
| No Fleetbase HTTP from mobile | API client base URL is Porterchain only       |
| No business logic in UI       | Zod validates forms; server decides outcomes  |
| Server-side truth             | MMKV/offline queue is cache/replay only       |
| Reuse modules                 | Shared `shared/api` mirrors web BFF contracts |

Mobile apps sit at the **UI layer** only (masterrule §3.7).

---

## 2. Repository layout

Only these paths are used for mobile (no ad-hoc folders):

```
apps/
├── mobile-driver/          # Driver Expo app (execution, GPS, POD — future screens)
└── mobile-customer/        # Customer Expo app (tracking, bookings — future screens)

shared/
├── api/                    # @porterchain/mobile-api — HTTP client, TanStack Query, domain APIs
├── theme/                  # @porterchain/mobile-theme — light/dark, tokens, RTL-aware ThemeProvider
├── hooks/                  # @porterchain/mobile-hooks — online status, app state, a11y helpers
├── storage/                # @porterchain/mobile-storage — MMKV, Secure Store, offline queue
├── maps/                   # @porterchain/mobile-maps — react-native-maps config provider
├── notifications/          # @porterchain/mobile-notifications — Expo + Firebase FCM
├── components/             # @porterchain/mobile-components — FlashList, offline banner
└── mobile-ui/              # @porterchain/mobile-ui — primitives, bottom sheets, gesture root
```

Web-only hooks remain at `shared/hooks/useVisitorSession.ts` (not part of mobile package exports).

---

## 3. Applications

### 3.1 `apps/mobile-driver`

| Item       | Value                        |
| ---------- | ---------------------------- |
| Package    | `@porterchain/mobile-driver` |
| Entry      | `index.ts` → `App.tsx`       |
| API prefix | `/driver-api/v1/*`           |
| Scheme     | `porterchain-driver`         |
| Port (dev) | Expo default `8081`          |

**App structure (no feature screens):**

```
apps/mobile-driver/
├── App.tsx
├── index.ts
├── app.config.ts
├── metro.config.js          # monorepo watchFolders
├── babel.config.js          # reanimated plugin
└── src/
    ├── config/env.ts
    ├── forms/schemas.ts     # Zod (login shell)
    ├── navigation/
    │   ├── RootNavigator.tsx
    │   └── types.ts
    ├── providers/AppProviders.tsx
    └── store/app-store.ts   # Zustand session bootstrap
```

### 3.2 `apps/mobile-customer`

| Item       | Value                          |
| ---------- | ------------------------------ |
| Package    | `@porterchain/mobile-customer` |
| Entry      | `index.ts` → `App.tsx`         |
| API prefix | `/v1/*` (retail/customer)      |
| Scheme     | `porterchain-customer`         |
| Port (dev) | `8082`                         |

Same shell pattern as driver; `createCustomerApi` from shared API.

---

## 4. Shared packages

### 4.1 `@porterchain/mobile-api` (`shared/api`)

| Module            | Responsibility                                    |
| ----------------- | ------------------------------------------------- |
| `client.ts`       | `createApiClient` — fetch, auth header, 401 hook  |
| `query-client.ts` | TanStack Query defaults (stale time, retry rules) |
| `driver.ts`       | Driver endpoint facades                           |
| `customer.ts`     | Customer endpoint facades                         |
| `offline.ts`      | Offline action types                              |

**No Fleetbase URLs.** Base URL: `EXPO_PUBLIC_API_URL`.

### 4.2 `@porterchain/mobile-theme` (`shared/theme`)

- `lightColors` / `darkColors` aligned with web portals
- `ThemeProvider` — system / light / dark preference
- `I18nManager.isRTL` exposed on theme for RTL layouts
- Tokens: spacing, radii, typography

### 4.3 `@porterchain/mobile-storage` (`shared/storage`)

| Store             | Use                                                   |
| ----------------- | ----------------------------------------------------- |
| **MMKV**          | Preferences, offline queue, non-sensitive cache       |
| **Secure Store**  | Access/refresh tokens, user ids                       |
| **Offline queue** | Action replay adapter (pairs with API sync endpoints) |

Business state is **not** authoritative in MMKV — server is source of truth.

### 4.4 `@porterchain/mobile-maps` (`shared/maps`)

- `MapsProvider` — Google Maps API key from env
- Types for markers/regions
- Display only; routing/GPS truth from Porterchain API (Fleetbase adapter server-side)

### 4.5 `@porterchain/mobile-notifications` (`shared/notifications`)

- Expo notification permissions
- `@react-native-firebase/messaging` token + foreground handlers
- Registers with Notification Engine via Porterchain API (`/push/register`)

### 4.6 `@porterchain/mobile-hooks` (`shared/hooks/mobile`)

- `useOnlineStatus` — NetInfo for offline-ready UX
- `useAppState` — foreground/background
- `a11yProps` — accessibility label helpers

### 4.7 `@porterchain/mobile-ui` (`shared/mobile-ui`)

Enterprise design system — see **`MOBILE_DESIGN_SYSTEM.md`**.

- **Layout:** `Screen`, `Divider`, `Spacer`
- **Typography:** `Display`, `Headline`, `Title`, `Body`, `Label`, `Caption`, `Text`
- **Actions:** `Button` (primary/secondary/ghost/outline/danger)
- **Surfaces:** `Card`, `CardHeader`
- **Forms:** `Input`, `SearchInput`
- **Data:** `ListItem`, `ListSection`, `DataTable`, `Badge`, `StatusChip`
- **Feedback:** `ToastProvider`, `useToast`, `Dialog`, `SheetModal`, `AppBottomSheet`
- **Loading:** `Skeleton`, `SkeletonCard`, `SkeletonList`
- **Charts:** `BarChart`, `Sparkline`, `MetricCard`
- **Logistics:** `Timeline`, `MapFrame`
- **States:** `LoadingState`, `EmptyState`, `ErrorState`, `SuccessState`
- **Motion:** `FadeIn*`, `PressableScale`, `AnimatedView`
- `MobileUiProvider` — Gesture Handler + Bottom Sheet modal provider

### 4.8 `@porterchain/mobile-components` (`shared/components`)

- `AppFlashList` — Shopify FlashList
- `OfflineBanner`, `EmptyState`
- Composed patterns built on `mobile-ui` + `theme`

---

## 5. Configured stack

| Technology            | Version / package             | Role                                       |
| --------------------- | ----------------------------- | ------------------------------------------ |
| **TypeScript**        | 5.9                           | Strict mode in apps + shared               |
| **Expo**              | SDK 52                        | Build, native modules, dev client          |
| **React Navigation**  | v7 native-stack + bottom-tabs | Navigation shell (tabs added with screens) |
| **TanStack Query**    | v5                            | Server state, cache, retries               |
| **Zustand**           | v5                            | Client session bootstrap                   |
| **React Hook Form**   | v7                            | Forms (schemas present, screens later)     |
| **Zod**               | v3                            | Input validation                           |
| **MMKV**              | v3                            | Fast local storage                         |
| **Expo Secure Store** | v14                           | Token storage                              |
| **Firebase**          | RN Firebase v21               | FCM push                                   |
| **Google Maps**       | react-native-maps             | Map display                                |
| **Reanimated**        | v3                            | Animations                                 |
| **Gesture Handler**   | v2                            | Gestures, navigation                       |
| **Bottom Sheets**     | @gorhom/bottom-sheet v5       | Modal sheets                               |
| **FlashList**         | v1                            | Performant lists                           |

---

## 6. Provider tree (both apps)

```
SafeAreaProvider
└── ThemeProvider (light / dark / system)
    └── QueryClientProvider
        └── MapsProvider
            └── MobileUiProvider (GestureHandlerRootView + BottomSheetModalProvider)
                └── RootNavigator
```

Future additions (with screens):

- Auth provider (Clerk + Porterchain JWT exchange for driver)
- Offline sync provider (flush queue on `useOnlineStatus`)
- Push registration provider

---

## 7. Offline-ready design

```
User action (future screen)
    ↓
TanStack Query mutation OR offline queue enqueue (MMKV)
    ↓
When online → POST /offline/queue + /offline/sync (driver API)
    ↓
Porterchain API → offline executor → Application Services
    ↓
Fleetbase Adapter (when action requires execution)
```

`OfflineBanner` in `mobile-components` surfaces NetInfo state.

---

## 8. Dark mode, RTL, accessibility

| Concern           | Implementation                                                                     |
| ----------------- | ---------------------------------------------------------------------------------- |
| **Dark mode**     | `ThemeProvider` + `userInterfaceStyle: "automatic"` in app.config                  |
| **RTL**           | `theme.isRTL` from `I18nManager`; use `start`/`end` spacing when screens are built |
| **Accessibility** | `a11yProps()`, `accessibilityRole` on banners; minimum touch targets in `Button`   |

---

## 9. Environment variables

| Variable                                              | Apps         | Purpose                                        |
| ----------------------------------------------------- | ------------ | ---------------------------------------------- |
| `EXPO_PUBLIC_API_URL`                                 | both         | Porterchain API base (`http://localhost:8001`) |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`                     | both         | Maps display                                   |
| `GOOGLE_SERVICES_JSON` / `GOOGLE_SERVICES_INFO_PLIST` | driver (EAS) | Firebase native config                         |

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md).

---

## 10. Monorepo wiring

**pnpm workspaces** (`pnpm-workspace.yaml`):

- `apps/mobile-driver`, `apps/mobile-customer`
- All `shared/*` mobile packages

**Metro** (`metro.config.js` per app):

- `watchFolders` → monorepo root
- `disableHierarchicalLookup` for consistent resolution

**Scripts** (root `package.json`):

```bash
pnpm dev:mobile-driver
pnpm dev:mobile-customer
```

---

## 11. API boundaries

### Driver mobile → Porterchain

| Domain                 | API prefix                     | Service (server)             |
| ---------------------- | ------------------------------ | ---------------------------- |
| Auth                   | `/driver-api/v1/auth/*`        | `driver_engine`              |
| Dashboard, jobs, shift | `/driver-api/v1/*`             | `porterchain_driver/*`       |
| Push                   | `/driver-api/v1/push/register` | `notification_engine`        |
| Offline                | `/driver-api/v1/offline/*`     | `porterchain_driver/offline` |

### Customer mobile → Porterchain

| Domain   | API prefix        | Service (server) |
| -------- | ----------------- | ---------------- |
| Bookings | `/v1/bookings`    | `booking_engine` |
| Tracking | `/v1/tracking/*`  | `booking_engine` |
| Profile  | `/v1/customers/*` | customer routers |

**Never:** `http://fleetbase:8000`, merchant API, admin API from mobile.

---

## 12. What is intentionally not implemented

Per scaffold scope:

- Feature screens (login, jobs, POD, tracking, etc.)
- Tab navigators and deep links
- Clerk integration in customer app
- Background location tasks
- EAS production profiles for customer app
- Screen-level React Hook Form flows

The **Bootstrap** placeholder screen confirms the shell only.

---

## 13. Next implementation phases

1. **Auth** — Clerk + Porterchain JWT; secure token storage
2. **Driver execution** — jobs, navigation, shift, POD (mirror driver-portal API usage)
3. **Customer retail** — tracking, booking history
4. **Push** — FCM registration on login; notification deep links
5. **Offline** — wire `createOfflineQueue` to driver sync endpoints
6. **Tests** — Detox / Maestro for critical flows

---

## 14. Related documents

- [masterrule.md](./masterrule.md)
- [DRIVER_ARCHITECTURE_REPORT.md](./DRIVER_ARCHITECTURE_REPORT.md)
- [DRIVER_INTEGRATION_MATRIX.md](./DRIVER_INTEGRATION_MATRIX.md)
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
