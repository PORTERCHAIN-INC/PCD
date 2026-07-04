# Mobile Production Readiness

**Audit date:** June 30, 2026  
**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Apps:** `@porterchain/mobile-driver`, `@porterchain/mobile-customer`

---

## Executive summary

| App          | Readiness | Verdict                                                                                                          |
| ------------ | --------- | ---------------------------------------------------------------------------------------------------------------- |
| **Driver**   | **72%**   | Feature-complete for field ops; needs Firebase credentials in CI, real CDN upload, Clerk prod sign-in, E2E tests |
| **Customer** | **62%**   | Core retail flows work; needs store assets, EAS project ID, Firebase files, payment recovery UI                  |

Architecture boundaries are **sound**: mobile calls Porterchain API only (`EXPO_PUBLIC_API_URL`), never Fleetbase directly. Gaps are operational (EAS, Firebase, Clerk), compliance (Stripe webhook-only), and hardening (uploads, tests, crash reporting).

---

## Readiness checklist

### Architecture & API

| Item                              | Driver | Customer | Notes                              |
| --------------------------------- | ------ | -------- | ---------------------------------- |
| Porterchain API only              | ✅     | ✅       | No `:8000` Fleetbase URLs          |
| UI layer only (masterrule §3)     | ✅     | ✅       | Zod/forms; server decides outcomes |
| Shared package reuse              | ✅     | ✅       | 11 shared mobile packages          |
| Server-side pricing/booking truth | ✅     | ✅       | Quotes/bookings via `/v1/*`        |

### Auth (Clerk)

| Item                           | Driver | Customer | Notes                                                          |
| ------------------------------ | ------ | -------- | -------------------------------------------------------------- |
| `@clerk/clerk-expo` dependency | ✅     | ✅       | Added in audit                                                 |
| ClerkBridge provider           | ✅     | ✅       | `shared/mobile-security`                                       |
| Production sign-in UI          | ⚠️     | ⚠️       | Email + button; no Clerk `SignIn` component yet                |
| Dev token bypass               | ⚠️     | ⚠️       | `"dev"` fallback when Clerk unset — **disable in prod builds** |
| JWT refresh (driver)           | ✅     | N/A      | `POST /driver-api/v1/auth/refresh`                             |

### Release & build

| Item                      | Driver | Customer | Notes                                                                                      |
| ------------------------- | ------ | -------- | ------------------------------------------------------------------------------------------ |
| `eas.json`                | ✅     | ✅       | Customer added in audit                                                                    |
| App icons / splash assets | ✅     | ❌       | Customer needs `assets/`                                                                   |
| EAS `projectId`           | ✅     | ⚠️       | Set `EAS_PROJECT_ID` for customer                                                          |
| Firebase native config    | ⚠️     | ⚠️       | Paths configured; files in `credentials/` required                                         |
| Production env in EAS     | ⚠️     | ⚠️       | Add `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`, `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` via EAS secrets |

### Field operations (driver)

| Item                         | Status | Notes                                              |
| ---------------------------- | ------ | -------------------------------------------------- |
| Jobs, shift, GPS, navigation | ✅     | Foreground + background GPS buffer                 |
| POD camera capture           | ✅     | `expo-image-picker` wired in audit                 |
| POD file upload to CDN       | ❌     | Stub `cdn.porterchain.local` — needs presigned API |
| OTP verify                   | ✅     | Fixed offline/online path in audit                 |
| JobDetail pickup stop        | ✅     | Fixed `pickup_stop_id` guard in audit              |
| `deliverStop`                | ✅     | Wired on Job Detail in audit                       |

### Retail (customer)

| Item                              | Status | Notes                                  |
| --------------------------------- | ------ | -------------------------------------- |
| Quote → booking → Stripe checkout | ✅     | Hosted checkout via `expo-web-browser` |
| Stripe webhook-only confirmation  | ✅     | Removed "I've paid" bypass in audit    |
| Payment retry UI                  | ❌     | `retryPayment` API unused              |
| Guest/public tracking             | ❌     | All routes behind auth                 |
| Customer offline server sync      | ❌     | Adapter `sync` stubbed                 |

### Notifications & deep links

| Item                      | Status | Notes                                                |
| ------------------------- | ------ | ---------------------------------------------------- |
| FCM token registration    | ✅     | Driver + customer push services                      |
| Permission before token   | ✅     | Fixed in audit                                       |
| Cold-start push deep link | ✅     | `getInitialNotification` + `onNotificationOpenedApp` |
| Custom scheme cold start  | ✅     | `useAppLinking` + `expo-linking`                     |
| Universal links (HTTPS)   | ❌     | No `associatedDomains` / intent filters              |

### Security

| Item                      | Status | Notes                            |
| ------------------------- | ------ | -------------------------------- |
| Secure token storage      | ✅     | Expo Secure Store                |
| Biometric / PIN lock      | ✅     | `SecurityShell`                  |
| Session timeout + refresh | ✅     | Driver refresh rotation          |
| Certificate pinning       | ❌     | Disabled by default              |
| Security audit events     | ✅     | `POST /v1/security/audit-events` |

### Observability & QA

| Item                     | Status | Notes                     |
| ------------------------ | ------ | ------------------------- |
| Performance dashboard    | ✅     | Dev/diagnostic metrics    |
| Crash reporting (Sentry) | ❌     | masterrule §16 gap        |
| E2E / Maestro / Detox    | ❌     | No automated mobile tests |
| CI mobile lint           | ⚠️     | `tsc --noEmit` per app    |

---

## Blockers before App Store / Play Store

### P0 — must fix

1. **Firebase credentials** — commit or inject `google-services.json` / `GoogleService-Info.plist` via EAS secrets for both apps.
2. **Clerk production auth** — wire Clerk `SignIn`; remove dev token paths in production builds (`__DEV__` guard or env flag).
3. **EAS secrets** — `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`, `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY` in preview/production profiles.
4. **Customer store assets** — icon, splash, adaptive icon (mirror driver `assets/`).
5. **Real file upload** — replace driver offline `uploadFile` CDN stub with API presigned upload.

### P1 — should fix

6. Customer `EAS_PROJECT_ID` and first EAS build.
7. Payment retry screen for failed Stripe checkouts.
8. Universal link configuration for marketing/email deep links.
9. Sentry or equivalent crash SDK.
10. Maestro E2E for sign-in, booking, POD, push tap.

### P2 — post-launch

11. Guest tracking flow (public order lookup without full account).
12. Customer offline server reconciliation.
13. Certificate pinning with production pins.
14. In-app turn-by-turn navigation.

---

## Environment variables (mobile)

| Variable                            | Driver       | Customer     | EAS prod                 |
| ----------------------------------- | ------------ | ------------ | ------------------------ |
| `EXPO_PUBLIC_API_URL`               | ✅           | ✅           | ✅                       |
| `EXPO_PUBLIC_APP_KIND`              | `driver`     | `customer`   | ✅                       |
| `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` | .env.example | .env.example | **Add secret**           |
| `EXPO_PUBLIC_GOOGLE_MAPS_API_KEY`   | .env.example | .env.example | **Add secret**           |
| `GOOGLE_SERVICES_JSON`              | app.config   | app.config   | **Add secret**           |
| `GOOGLE_SERVICES_INFO_PLIST`        | app.config   | app.config   | **Add secret**           |
| `EAS_PROJECT_ID`                    | extra.eas    | extra.eas    | Customer: create project |

---

## Audit remediation (this session)

| Fix                                                  | Area                       |
| ---------------------------------------------------- | -------------------------- |
| Push permission before FCM token                     | Firebase                   |
| Cold-start FCM + URL deep links                      | Notifications / Navigation |
| Stripe "Check payment status" (webhook-only)         | Payments                   |
| JobDetail pickup/deliver stop IDs                    | Driver / Fleetbase         |
| POD camera/library capture                           | Driver                     |
| OTP verify via offline executor                      | Driver                     |
| `@clerk/clerk-expo` dependency                       | Clerk                      |
| Customer `eas.json` + Firebase paths in `app.config` | Release                    |
| Removed orphaned `biometric.ts`                      | Security                   |

---

## Related documents

- [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md)
- [MOBILE_SECURITY_REPORT.md](./MOBILE_SECURITY_REPORT.md)
- [MOBILE_PERFORMANCE_REPORT.md](./MOBILE_PERFORMANCE_REPORT.md)
- [MOBILE_UI_REPORT.md](./MOBILE_UI_REPORT.md)
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
- [masterrule.md](./masterrule.md)
