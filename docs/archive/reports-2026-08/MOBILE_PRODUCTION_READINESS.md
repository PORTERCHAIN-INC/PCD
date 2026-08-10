# Mobile Production Readiness

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Apps:** `@porterchain/mobile-driver`, `@porterchain/mobile-customer`

> **Platform status:** overall Porterchain is **not production ready** — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md). Mobile is assessed here as app-store/beta readiness, not whole-platform certification.

---

## Executive Summary

| App          | Readiness | Verdict                                                                                                                                                                                                                |
| ------------ | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Driver**   | **78%**   | Core field execution is wired: Clerk, JWT refresh, jobs, navigation, POD, offline sync, push, SOS. Remaining gaps are production Firebase/EAS secrets, upload hardening, crash reporting, and field tests.             |
| **Customer** | **68%**   | Retail flows are wired: quote, booking, Stripe checkout, tracking, notifications, support. Remaining gaps are store assets, `EAS_PROJECT_ID`, payment retry UX, guest tracking, and server-side customer offline sync. |

Architecture boundaries are sound: both apps call **Porterchain API only** (`EXPO_PUBLIC_API_URL`), never Fleetbase or merchant/admin APIs directly.

---

## Architecture Readiness

| Item                   | Driver | Customer | Notes                                                     |
| ---------------------- | ------ | -------- | --------------------------------------------------------- |
| Porterchain API only   | ✅     | ✅       | Driver `/driver-api/v1/*`; customer `/v1/*`               |
| Shared mobile packages | ✅     | ✅       | 11 packages under `shared/`                               |
| Secure API client      | ✅     | ✅       | `createSecureApiClient`                                   |
| Clerk integration      | ✅     | ✅       | `@clerk/clerk-expo` + mobile security package             |
| Secure token storage   | ✅     | ✅       | Secure Store via app auth stores                          |
| Offline architecture   | ✅     | ⚠        | Driver syncs to server; customer adapter is local/stubbed |
| Maps display           | ✅     | ✅       | `@porterchain/mobile-maps` + Google Maps config           |
| Push notifications     | ✅     | ✅       | FCM native config paths and register flows                |

---

## Driver App Readiness

| Capability              | Status | Evidence                                                 |
| ----------------------- | ------ | -------------------------------------------------------- |
| Sign-in                 | ✅     | `ClerkSignInPanel` → `/driver-api/v1/auth/login`         |
| Refresh rotation        | ✅     | `createSecureApiClient` calls `/auth/refresh`            |
| Dashboard               | ✅     | Home screen                                              |
| Jobs / detail / queue   | ✅     | Jobs stack                                               |
| Navigation + GPS        | ✅     | Navigation screen, `expo-location`, background config    |
| POD                     | ✅     | `PodScreen`, image picker, OTP, signature/file URL flows |
| Shift / availability    | ✅     | Shift tab                                                |
| Earnings                | ✅     | Earnings tab                                             |
| Offline sync            | ✅     | MMKV queue, 30s auto-sync, server executor               |
| Push / notifications    | ✅     | FCM adapter + notification screen                        |
| Support / SOS           | ✅     | Support and SOS screens                                  |
| Performance diagnostics | ✅     | Performance screen/package                               |

### Driver Blockers Before Store Release

| Priority | Item                                                                                                             |
| -------- | ---------------------------------------------------------------------------------------------------------------- |
| P0       | Inject real Firebase native credentials through EAS secrets (`google-services.json`, `GoogleService-Info.plist`) |
| P0       | Replace any POD/upload placeholder paths with production presigned upload flow                                   |
| P0       | Run field tests for background GPS, offline POD replay, and SOS                                                  |
| P1       | Add crash reporting (Sentry or equivalent)                                                                       |
| P1       | Add Maestro/Detox smoke tests for sign-in, job accept, POD, offline sync, push tap                               |
| P2       | Certificate pinning and device integrity policy                                                                  |

---

## Customer App Readiness

| Capability           | Status | Evidence                                               |
| -------------------- | ------ | ------------------------------------------------------ |
| Sign-in              | ✅     | Clerk panel + customer secure API client               |
| Dashboard            | ✅     | Home screen                                            |
| Quote / booking      | ✅     | Quote, Booking, Draft screens                          |
| Stripe checkout      | ✅     | Hosted checkout via WebBrowser                         |
| Booking confirmation | ✅     | Server confirmation polling                            |
| Tracking / live map  | ✅     | Tracking stack and live map                            |
| Notifications        | ✅     | FCM + notification center                              |
| Support / claims     | ✅     | Profile stack                                          |
| Invoices / receipts  | ✅     | Profile stack screens                                  |
| Offline UX           | ⚠      | Local queue provider; server reconciliation incomplete |
| Payment retry        | ⚠      | API client method exists; full UX still partial        |
| Guest tracking       | ❌     | Auth-gated app flow                                    |

### Customer Blockers Before Store Release

| Priority | Item                                                                        |
| -------- | --------------------------------------------------------------------------- |
| P0       | Add production app icons/splash/adaptive assets                             |
| P0       | Set production `EAS_PROJECT_ID` and run first store-profile build           |
| P0       | Inject Firebase native credentials through EAS secrets                      |
| P1       | Finish payment retry UX for failed/canceled checkout                        |
| P1       | Decide whether guest tracking is required before launch                     |
| P1       | Add universal links (`associatedDomains` / Android intent filters)          |
| P2       | Add server-backed customer offline reconciliation or document as local-only |

---

## Release / Build Status

| Item                | Driver | Customer | Notes                                             |
| ------------------- | ------ | -------- | ------------------------------------------------- |
| `eas.json`          | ✅     | ✅       | Both define development/preview/production        |
| Node in EAS         | ✓      | ✓        | EAS uses `24.18.0`; matches repo `.nvmrc`         |
| App icons           | ✅     | ⚠        | Customer config lacks explicit icon/adaptive icon |
| Splash              | ✅     | ⚠        | Customer splash has background only               |
| iOS bundle id       | ✅     | ✅       | `com.porterchain.PCD`, `com.porterchain.customer` |
| Android package     | ✅     | ✅       | Driver/customer package ids set                   |
| Firebase file paths | ✅     | ✅       | Credentials must be supplied securely             |
| EAS submit metadata | ✅     | ⚠        | Customer lacks `ascAppId`                         |

---

## Environment Variables

| Variable                            | Driver          | Customer | Production Requirement                          |
| ----------------------------------- | --------------- | -------- | ----------------------------------------------- |
| `EXPO_PUBLIC_API_URL`               | ✅              | ✅       | `https://api.porterchain.com` or production API |
| `EXPO_PUBLIC_APP_KIND`              | ✅              | ✅       | `driver` / `customer`                           |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | Required        | Required | EAS secret                                      |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`   | Required        | Required | EAS secret                                      |
| `GOOGLE_SERVICES_JSON`              | Required        | Required | EAS secret or credentials path                  |
| `GOOGLE_SERVICES_INFO_PLIST`        | Required        | Required | EAS secret or credentials path                  |
| `EAS_PROJECT_ID`                    | Fixed in config | Required | Customer project id                             |

---

## Security And Compliance

| Item                        | Status | Notes                                                             |
| --------------------------- | ------ | ----------------------------------------------------------------- |
| Secure token storage        | ✅     | Secure Store                                                      |
| Clerk-only auth             | ✅     | No legacy auth path for production                                |
| Dev token bypass            | ⚠      | Present for local/dev; must be disabled in production builds      |
| Biometric/PIN shell         | ✅     | Mobile security package                                           |
| Security audit events       | ✅     | Mobile security emitter                                           |
| Certificate pinning         | ❌     | Package includes network pinning support; not enforced by default |
| Stripe webhook confirmation | ✅     | Customer uses hosted checkout + server confirmation               |

---

## QA Checklist

| Test                                 | Driver                | Customer                           |
| ------------------------------------ | --------------------- | ---------------------------------- |
| Typecheck (`pnpm --filter ... lint`) | Required              | Required                           |
| EAS preview build                    | Required              | Required                           |
| Sign-in with production Clerk        | Required              | Required                           |
| Push permission + token registration | Required              | Required                           |
| Deep link cold start                 | Required              | Required                           |
| Offline replay                       | Required              | Required (local-only expectations) |
| Crash reporting smoke                | Required before store | Required before store              |
| Store release build                  | Required              | Required                           |

---

## Related Documents

| Document                                                                                 | Purpose                        |
| ---------------------------------------------------------------------------------------- | ------------------------------ |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md)                         | Canonical mobile architecture  |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md)                         | Mobile surfaces and navigation |
| [docs/archive/MOBILE_SECURITY_REPORT.md](./docs/archive/MOBILE_SECURITY_REPORT.md)       | Historical security audit      |
| [docs/archive/MOBILE_PERFORMANCE_REPORT.md](./docs/archive/MOBILE_PERFORMANCE_REPORT.md) | Historical performance audit   |
| [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md)                       | Driver-specific rollout        |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)                                   | Env reference                  |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
