# Porterchain Driver Mobile App


**Type:** README
**masterrule:** [§21](../../masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05


Expo SDK 52 driver execution app. It calls **Porterchain API only** (`/driver-api/v1/*`); Fleetbase integration stays server-side through the Porterchain API and Fleetbase adapter.

---

## Run

```bash
pnpm dev:mobile-driver
```

Expo defaults to port `8081`. The app expects the API on `EXPO_PUBLIC_API_URL` (`http://localhost:8001` locally).

---

## Architecture

```
mobile-driver (Expo)
    ↓ HTTPS
Porterchain API :8001 /driver-api/v1/*
    ↓
porterchain_driver + driver_engine
    ↓
Fleetbase adapter → Fleetbase :8000
```

Shared packages used by the app include:

- `@porterchain/mobile-api`
- `@porterchain/mobile-security`
- `@porterchain/mobile-offline`
- `@porterchain/mobile-notifications`
- `@porterchain/mobile-performance`
- `@porterchain/mobile-maps`
- `@porterchain/mobile-ui`

---

## Tabs

| Tab | Features |
| --- | -------- |
| **Home** | Dashboard, today’s stops/earnings, quick actions |
| **Jobs** | Current/upcoming/completed jobs, job detail, assignment queue, POD, incident |
| **Navigation** | Map, GPS pings, route/navigation session from API |
| **Earnings** | Today/week/month earnings and wallet summary |
| **Shift** | Online/offline, start/end shift, breaks |
| **More** | Profile, notifications, offline sync, support, SOS, settings, performance |

---

## Execution Flows

| Flow | API |
| ---- | --- |
| Accept / reject job | `POST /driver-api/v1/orders/{id}/accept|reject` |
| Route execution | `GET /routes/assigned`, stop arrive/deliver/exception |
| POD | `pod-photo`, `pod-signature`, `pod-complete`, `orders/{id}/otp` |
| Navigation | `GET /navigation/session`, map rendering via mobile maps |
| Realtime GPS | `expo-location` → `POST /location` |
| Shift / availability | `/shift/*`, `/availability` |
| Offline sync | MMKV queue → `/offline/queue`, `/offline/sync` |
| Push | FCM → `/push/register` |
| Support / incident / SOS | `/support`, `/incidents`, `/emergency` |

---

## Auth

Production auth uses Clerk:

1. `ClerkSignInPanel` signs in with Clerk.
2. The app exchanges Clerk bearer + email at `POST /driver-api/v1/auth/login`.
3. Porterchain returns access and refresh tokens.
4. Tokens are stored securely; `createSecureApiClient` refreshes via `/auth/refresh` on 401.

Local development can show `DevEmailSignInPanel` only when `EXPO_PUBLIC_APP_ENV=local` and the API is configured for local dev bypass.

---

## Environment

```bash
EXPO_PUBLIC_API_URL=http://localhost:8001
EXPO_PUBLIC_APP_KIND=driver
EXPO_PUBLIC_APP_ENV=local
EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY=
EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=
GOOGLE_SERVICES_JSON=
GOOGLE_SERVICES_INFO_PLIST=
```

Production values should be supplied through EAS secrets/profiles.

---

## Release Notes

- EAS config exists in `eas.json`.
- iOS bundle id / Android package: `com.porterchain.PCD`.
- Firebase native credential files are referenced from `app.config.ts`; do not commit real credentials.
- Before store release, run field tests for background GPS, offline POD replay, push tap deep links, and SOS.

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [../../MOBILE_ARCHITECTURE_REPORT.md](../../MOBILE_ARCHITECTURE_REPORT.md) | Mobile architecture |
| [../../MOBILE_PRODUCTION_READINESS.md](../../MOBILE_PRODUCTION_READINESS.md) | Mobile readiness |
| [../../DRIVER_PLATFORM.md](../../DRIVER_PLATFORM.md) | Driver backend/API architecture |
| [../../DRIVER_PRODUCTION_READINESS.md](../../DRIVER_PRODUCTION_READINESS.md) | Driver rollout posture |
---

## Governance

| Document | Role |
| -------- | ---- |
| [../../masterrule.md](../../masterrule.md) | Architecture SSOT |
| [../../REPOSITORY_STRUCTURE.md](../../REPOSITORY_STRUCTURE.md) | Monorepo layout |

