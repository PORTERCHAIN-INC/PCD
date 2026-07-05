# Porterchain Driver App — Connections & Integrations

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

Single reference for how the **mobile-driver** app connects to backends, stores, maps, and Apple distribution.  
App path: `apps/mobile-driver` · Stack: **Expo SDK 52** · **React Native 0.76**

---

## Summary

| Integration                                             | Used?   | Notes                                                                        |
| ------------------------------------------------------- | ------- | ---------------------------------------------------------------------------- |
| **Porterchain API** (`EXPO_PUBLIC_API_URL`)             | Yes     | Auth, routes, stops, POD uploads, location                                   |
| **Google Maps SDK** (`EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`) | Yes     | Route map tiles via `react-native-maps`                                      |
| **Firebase / FCM**                                      | Yes     | `@react-native-firebase/messaging` — registers token via `/push/register`    |
| **Push notifications**                                  | Partial | Implemented in app; production delivery requires Firebase credentials on API |
| **Expo / EAS**                                          | Yes     | Cloud builds, project linking, optional OTA config (updates disabled)        |
| **App Store Connect**                                   | Yes     | iOS distribution via EAS Submit                                              |
| **Apple Developer Program**                             | Yes     | Signing, bundle ID, TestFlight / App Store                                   |

---

## Environment variables

### Driver app (`apps/mobile-driver/.env`)

Copy from `.env.example`. **Never commit** `.env`, `credentials/`, or `*.p8`.

| Variable                          | Required    | Description                                                                      |
| --------------------------------- | ----------- | -------------------------------------------------------------------------------- |
| `EXPO_PUBLIC_API_URL`             | Yes (prod)  | API base URL, **no trailing slash**. Inlined at build time by Metro/EAS.         |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` | Yes (maps)  | Google Maps SDK for iOS/Android. Restrict in Google Cloud Console.               |
| `APPLE_ASC_KEY_PATH`              | Submit only | Path to App Store Connect API private key, e.g. `./credentials/AuthKey.p8`       |
| `APPLE_ASC_KEY_ID`                | Submit only | Key ID from App Store Connect → Integrations → App Store Connect API             |
| `APPLE_ASC_ISSUER_ID`             | Submit only | Issuer ID from same page                                                         |
| `EXPO_TOKEN`                      | Optional    | Expo access token for non-interactive EAS (`expo.dev` → Account → Access Tokens) |
| `VERIFY_ASC_KEY`                  | Optional    | Set to `0` to skip ASC key preflight in deploy script (default `1`)              |

**Code:** `src/config/env.ts` — only **static** `process.env.EXPO_PUBLIC_*` access (required for EAS production inlining).

### API base URL by environment

| Context                     | `EXPO_PUBLIC_API_URL`                              | Set in                                            |
| --------------------------- | -------------------------------------------------- | ------------------------------------------------- |
| Local dev (simulator)       | `http://localhost:8001` or `http://127.0.0.1:8001` | `.env`                                            |
| Local dev (physical device) | `http://<YOUR_LAN_IP>:8001`                        | `.env`                                            |
| Android emulator → host API | `http://10.0.2.2:8001`                             | `.env`                                            |
| EAS development             | `http://127.0.0.1:8001`                            | `eas.json` → `build.development.env`              |
| EAS preview / production    | `https://api.porterchain.com`                      | `eas.json` → `build.preview` / `build.production` |

Default if unset: `http://localhost:8001`.

### API server (root `.env`) — links _to_ the driver app

These are **not** read by the mobile app; they configure invite emails and the public drive page.

| Variable                                              | Default                 | Purpose                                                                            |
| ----------------------------------------------------- | ----------------------- | ---------------------------------------------------------------------------------- |
| `DRIVER_PORTAL_BASE_URL`                              | `http://localhost:3003` | Base URL for password-setup links in emails: `{base}/auth/driver-invite?token=...` |
| `DRIVER_APP_DOWNLOAD_URL`                             | (empty)                 | Marketing drive page in approval emails                                            |
| `DRIVER_APP_IOS_URL`                                  | (empty)                 | Direct App Store URL in emails                                                     |
| `DRIVER_APP_ANDROID_URL`                              | (empty)                 | Direct Play Store URL in emails                                                    |
| `DRIVER_INVITE_TOKEN_EXPIRE_SECONDS`                  | `604800` (7 days)       | Invite token TTL                                                                   |
| `AUTH_DRIVER_INVITE_VALIDATE_MAX_ATTEMPTS_PER_MINUTE` | `30`                    | Rate limit                                                                         |
| `AUTH_DRIVER_INVITE_ACCEPT_MAX_ATTEMPTS_PER_MINUTE`   | `15`                    | Rate limit                                                                         |

**Public website** (optional): `NEXT_PUBLIC_DRIVER_APP_IOS_URL`, `NEXT_PUBLIC_DRIVER_APP_ANDROID_URL` on `website/` for the drive page.

**Google Maps (root):** `GOOGLE_MAPS_BROWSER_API_KEY` / `GOOGLE_MAPS_SERVER_API_KEY` are for web/API — **not** the driver app. Driver uses its own `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`.

---

## Porterchain API

All requests use `{EXPO_PUBLIC_API_URL}` as origin. Authenticated calls send:

| Header          | Value                                         |
| --------------- | --------------------------------------------- |
| `Authorization` | `Bearer <access_token>`                       |
| `X-User-Id`     | User id (string)                              |
| `X-Roles`       | `driver`                                      |
| `X-Driver-Id`   | Driver id (required for driver-scoped routes) |

**Client:** `src/services/apiClient.ts` · **Services:** `src/services/driverService.ts`, `src/services/driverInviteService.ts`

### Auth endpoints (no driver headers)

| Method | Path                           | Used by                                         |
| ------ | ------------------------------ | ----------------------------------------------- |
| `POST` | `/auth/login`                  | Login screen                                    |
| `POST` | `/auth/refresh`                | `src/auth/refresh.ts` (if refresh token stored) |
| `POST` | `/auth/driver-invite/validate` | Invite flow                                     |
| `POST` | `/auth/driver-invite/accept`   | Invite password setup                           |

Login body: `{ email, password }`. Response must include `access_token` and `driver_id`.

### Driver execution API (`/driver-api/v1`)

| Method | Path                                                      | Purpose                            |
| ------ | --------------------------------------------------------- | ---------------------------------- |
| `GET`  | `/driver-api/v1/routes/assigned`                          | Today’s assigned route             |
| `POST` | `/driver-api/v1/routes/{id}/start`                        | Start route                        |
| `GET`  | `/driver-api/v1/routes/{id}/stops`                        | Ordered stops + `route_polyline`   |
| `GET`  | `/driver-api/v1/me`                                       | Driver profile + document status   |
| `POST` | `/driver-api/v1/documents`                                | Upload compliance docs (multipart) |
| `POST` | `/driver-api/v1/routes/{id}/stops/{stopId}/arrive`        | Mark arrived                       |
| `POST` | `/driver-api/v1/routes/{id}/stops/{stopId}/deliver`       | Mark delivered                     |
| `POST` | `/driver-api/v1/routes/{id}/stops/{stopId}/exception`     | Report exception                   |
| `POST` | `/driver-api/v1/routes/{id}/stops/{stopId}/pod-photo`     | POD photo upload                   |
| `POST` | `/driver-api/v1/routes/{id}/stops/{stopId}/pod-signature` | POD signature upload               |

> **Note:** Proof-of-pickup (`pop-photo`) is not implemented in `routers/driver.py` as of 2026-07-05. Use POD endpoints after pickup completion.

### Legacy / companion driver routes (`/driver`)

| Method | Path                            | Purpose                   |
| ------ | ------------------------------- | ------------------------- |
| `GET`  | `/driver/stops/{stopId}`        | Stop detail               |
| `POST` | `/driver/stops/{stopId}/update` | Update stop status        |
| `POST` | `/driver/location`              | Background location pings |

### Other API paths used by the app

| Method  | Path                                | Purpose              |
| ------- | ----------------------------------- | -------------------- |
| `GET`   | `/routes/{routeId}/driver-earnings` | Earnings tab         |
| `PATCH` | `/routes/{routeId}`                 | Route status updates |

### Route polyline (maps)

- Polyline comes from `GET /driver-api/v1/routes/{id}/stops` field `route_polyline` (OSRM-encoded).
- Decoded in `src/lib/routePolyline.ts` with `@mapbox/polyline`.
- If missing, app draws straight lines between stop coordinates.
- **No direct OSRM URL** in the app — routing is server-side when ops optimizes the route in admin.

---

## Authentication & local storage

| Concern                 | Implementation                                                                                              |
| ----------------------- | ----------------------------------------------------------------------------------------------------------- |
| Token storage           | `expo-secure-store` (`src/auth/storage.ts`)                                                                 |
| Keys                    | `porterchain_driver_access_token`, `porterchain_driver_refresh_token`, `porterchain_driver_driver_id`, etc. |
| Session restore         | `AuthContext` loads secure store on launch                                                                  |
| Logout                  | Clears secure store + stops background location                                                             |
| Driver invite deep link | App route `/auth/driver-invite?token=...` (`app/auth/driver-invite.tsx`)                                    |

**Invite link format (from API emails):**  
`{DRIVER_PORTAL_BASE_URL}/auth/driver-invite?token=<opaque>`

For native builds, `DRIVER_PORTAL_BASE_URL` must point at a URL that opens the app or a web fallback that deep-links into the app scheme `porterchain-driver://`.

---

## Google Maps

| Item        | Value                                                                               |
| ----------- | ----------------------------------------------------------------------------------- |
| Library     | `react-native-maps` with `PROVIDER_GOOGLE`                                          |
| Env var     | `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`                                                   |
| Expo config | `app.config.ts` → `ios.config.googleMapsApiKey`, `android.config.googleMaps.apiKey` |
| iOS native  | `GMSApiKey` in `ios/PorterchainDriver/Info.plist` (set at prebuild from env)        |

**Google Cloud restrictions (recommended):**

- Enable **Maps SDK for iOS** and **Maps SDK for Android**
- Restrict by bundle/package: `com.porterchain.PCD`
- Do **not** reuse the web browser key (`GOOGLE_MAPS_BROWSER_API_KEY`)

Maps require a **development build** or production build — Expo Go may not apply custom native maps config.

---

## Firebase & push notifications

The driver app uses **Firebase Cloud Messaging** for push:

- Packages: `@react-native-firebase/app`, `@react-native-firebase/messaging`, `expo-notifications`
- Token registration: `src/services/push.ts` → `POST /push/register` on Porterchain API
- Auth remains Porterchain JWT — **not** Firebase Auth

Production push delivery requires `FIREBASE_CREDENTIALS_PATH` and related vars on the API/worker. Local dev works without push if credentials are unset.

---

## Expo & EAS

| Item           | Value                                                                                |
| -------------- | ------------------------------------------------------------------------------------ |
| Expo slug      | `porterchain-driver`                                                                 |
| Expo owner     | `porterchains-organization`                                                          |
| EAS project ID | `4beda39e-2c2c-4cda-b994-262e646438ca` (`app.config.ts` → `extra.eas.projectId`)     |
| URL scheme     | `porterchain-driver`                                                                 |
| OTA updates    | Disabled (`ios/PorterchainDriver/Supporting/Expo.plist` → `EXUpdatesEnabled: false`) |

### `eas.json` build profiles

| Profile       | Distribution | API URL                       | Notes                                   |
| ------------- | ------------ | ----------------------------- | --------------------------------------- |
| `development` | internal     | `http://127.0.0.1:8001`       | Dev client, iOS simulator               |
| `preview`     | internal     | `https://api.porterchain.com` | Device testing                          |
| `production`  | store        | `https://api.porterchain.com` | App Store; Node 22.14, Xcode 26.2 image |

**Production Google Maps key:** set as EAS secret (not only local `.env`):

```bash
cd apps/mobile-driver
npx eas-cli secret:create --scope project --name EXPO_PUBLIC_GOOGLE_MAPS_API_KEY --value "YOUR_KEY"
```

### NPM scripts (`package.json`)

| Script                      | Command                                                   |
| --------------------------- | --------------------------------------------------------- |
| `pnpm dev`                  | `expo start`                                              |
| `pnpm ios` / `pnpm android` | Native run                                                |
| `pnpm build:ios:production` | `eas build --platform ios --profile production`           |
| `pnpm build:ios:preview`    | EAS preview build                                         |
| `pnpm submit:ios`           | `eas submit --platform ios --profile production --latest` |

**Monorepo (repo root):** `pnpm dev:mobile-driver`, `pnpm build:mobile-driver`

### Deploy script

`scripts/deploy-driver-appstore.sh` from repo root:

```bash
./scripts/deploy-driver-appstore.sh build          # EAS production iOS build
./scripts/deploy-driver-appstore.sh submit         # Submit latest to ASC
./scripts/deploy-driver-appstore.sh build-submit   # Both
```

Requires: `apps/mobile-driver/.env` (ASC vars), `credentials/AuthKey.p8`, Expo login or `EXPO_TOKEN`.

---

## App Store Connect & Apple Developer

Configured in `eas.json` → `submit.production.ios`:

| Field         | Value                                     |
| ------------- | ----------------------------------------- |
| `appleTeamId` | `4XWFT5A8C3`                              |
| `ascAppId`    | `6781880626`                              |
| `appleId`     | Apple ID used for submit (see `eas.json`) |

### App identifiers (`app.config.ts`)

| Platform        | Identifier                                               |
| --------------- | -------------------------------------------------------- |
| iOS bundle ID   | `com.porterchain.PCD`                                    |
| Android package | `com.porterchain.PCD`                                    |
| Display name    | Porterchain Driver                                       |
| Version         | `1.0.0` (iOS `buildNumber` / Android `versionCode`: `1`) |

> Note: `.env.example` comments mention `com.porterchain.driver` for Maps restrictions; the **actual** bundle ID in the project is `com.porterchain.PCD`.

### App Store Connect API key (for EAS Submit)

1. App Store Connect → **Users and Access** → **Integrations** → **App Store Connect API**
2. Create key → download `AuthKey_<KEY_ID>.p8` (one-time)
3. Save as `apps/mobile-driver/credentials/AuthKey.p8` (gitignored)
4. Set in `apps/mobile-driver/.env`:
   - `APPLE_ASC_KEY_ID`
   - `APPLE_ASC_ISSUER_ID`
   - `APPLE_ASC_KEY_PATH=./credentials/AuthKey.p8`

Deploy script maps these to `EXPO_ASC_*` for EAS CLI.

### iOS capabilities & permissions

| Capability          | Config                                                           |
| ------------------- | ---------------------------------------------------------------- |
| Background location | `UIBackgroundModes`: `location`, `fetch`; `expo-location` plugin |
| Camera / photos     | POD photos, barcode scan, document upload                        |
| ATS                 | Local networking allowed (`NSAllowsLocalNetworking`) for dev     |

Entitlements file: `ios/PorterchainDriver/PorterchainDriver.entitlements` (currently empty dict — add capabilities in Apple Developer / EAS as needed).

---

## Device features (on-device only)

| Feature               | Package                                              | Backend                                   |
| --------------------- | ---------------------------------------------------- | ----------------------------------------- |
| Background GPS        | `expo-location`, `expo-task-manager`                 | `POST /driver/location` every ~20s / 80m  |
| Barcode scan          | `expo-camera`                                        | Local UI                                  |
| POD photo / signature | `expo-image-picker`, `react-native-signature-canvas` | Multipart uploads to `/driver-api/v1/...` |
| Secure auth           | `expo-secure-store`                                  | —                                         |

Location tracking does **not** work in Expo Go; use `npx expo run:ios` or an EAS build.

---

## Local development checklist

1. Start API: `pnpm dev:api` (port **8001**)
2. `cd apps/mobile-driver && cp .env.example .env`
3. Set `EXPO_PUBLIC_API_URL` (LAN IP for physical device)
4. Set `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` for map screen
5. `pnpm dev` — keep Metro running for Xcode Debug builds
6. For API invite emails locally, set root `.env` `DRIVER_PORTAL_BASE_URL` to a URL that reaches the app invite screen

---

## Files to keep secret (gitignored)

| Path                              | Contents                                                         |
| --------------------------------- | ---------------------------------------------------------------- |
| `apps/mobile-driver/.env`         | API URL, Maps key, ASC IDs                                       |
| `apps/mobile-driver/credentials/` | App Store Connect `.p8` key                                      |
| `AuthKey_*.p8` (repo root)        | Do not commit; use `credentials/AuthKey.p8` inside mobile-driver |

---

## Related docs & code

| Resource              | Location                                                               |
| --------------------- | ---------------------------------------------------------------------- |
| App README            | `apps/mobile-driver/README.md`                                         |
| Env loader            | `src/config/env.ts`                                                    |
| Expo config           | `app.config.ts`                                                        |
| EAS config            | `eas.json`                                                             |
| Deploy script         | `scripts/deploy-driver-appstore.sh`                                    |
| API driver router     | `apps/api/src/porterchain_api/routers/driver.py`                       |
| API auth / invites    | `apps/api/src/porterchain_api/` auth modules                           |
| Driver onboarding ops | `DRIVER-ONBOARDING-ARCHITECTURE.md`, `DRIVER-ONBOARDING-OPERATIONS.md` |

---

_Last verified: 2026-07-04. Firebase FCM is integrated for push; auth and execution data flow through Porterchain API on port 8001._
---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
| [OpenAPI](http://localhost:8001/docs)      | OpenAPI (local)   |
