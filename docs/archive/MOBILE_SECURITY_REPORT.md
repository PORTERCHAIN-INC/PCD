# Mobile Security Report

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §15  
**Package:** `@porterchain/mobile-security` (`shared/mobile-security/`)

---

## Executive Summary

Enterprise mobile security is implemented through a shared security layer used by both mobile apps. Clerk sign-in is wired, secure storage is used for tokens, driver refresh works through `createSecureApiClient`, and signed-in navigation is wrapped by `SecurityShell`.

**Security posture:** good for beta; production hardening remains before App Store / Play Store release.

| Area | Status | Notes |
| ---- | ------ | ----- |
| Clerk auth | ✅ | `ClerkSignInPanel` supports email/password and Google OAuth |
| Dev auth fallback | ⚠ | Local-only UI, but production EAS profiles must enforce Clerk keys |
| Secure token storage | ✅ | Expo Secure Store / secure session helpers |
| Driver refresh | ✅ | `/driver-api/v1/auth/refresh` on 401 retry |
| Customer auth | ✅ | Clerk bearer used with `/v1/auth/me` |
| PIN/biometric shell | ✅ | `SecurityShell`, `PinLockGate`, `BiometricGate` |
| Certificate pinning | ⚠ off | Support exists; not enforced |
| Device integrity | ⚠ adapter hook | `registerIntegrityAdapter()` available; production adapter needed |
| Audit events | ✅ | buffered and scrubbed |

---

## Security Package Capabilities

| Capability | Implementation | Status |
| ---------- | -------------- | ------ |
| Clerk bridge | `ClerkBridge`, `getClerkBearerToken`, `getClerkPrimaryEmail` | ✅ |
| Sign-in panels | `ClerkSignInPanel`, `DevEmailSignInPanel` | ✅ |
| Secure storage | `getSecureValue`, `setSecureValue`, secure session helpers | ✅ |
| Encrypted MMKV | `getEncryptedMmkvStore`, JSON helpers | ✅ |
| Session manager | persisted session, timeout, biometric/PIN flags | ✅ |
| Driver refresh | `refreshDriverSession`, `refreshAndPersistDriverSession` | ✅ |
| API client | `createSecureApiClient` with 401 retry/refresh | ✅ |
| Biometric | `BiometricGate`, service helpers | ✅ |
| PIN lock | `PinLockGate`, salted PIN hash | ✅ |
| Integrity | `IntegrityGate`, adapter registration | ⚠ adapter required |
| Pinning | `configureCertificatePinning`, `createPinningFetch` | ⚠ disabled by default |
| RBAC | `PermissionGate`, role/permission helpers | ✅ UI-only |
| Audit | `emitSecurityEvent`, buffer flush/config | ✅ |

---

## Provider Architecture

```
SecurityLayer
└── ClerkBridge
    └── MobileSecurityProvider
        └── ApiProvider (createSecureApiClient)
            └── OfflineSyncLayer
                └── NotificationLayer
                    └── RootNavigator
                        └── SecurityShell
                            └── MainTabs
```

Driver and customer each define `apps/mobile-*/src/providers/SecurityLayer.tsx` and wrap signed-in navigation with `SecurityShell`.

---

## Authentication Flows

### Driver

1. `ClerkSignInPanel` signs in with Clerk when `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY` is configured.
2. App reads Clerk bearer and primary email.
3. `POST /driver-api/v1/auth/login` exchanges Clerk identity for Porterchain driver JWT pair.
4. Access and refresh tokens are stored through the driver auth store / Secure Store.
5. `createSecureApiClient` refreshes via `POST /driver-api/v1/auth/refresh` after a 401, persists the new token, and retries the request.

### Customer

1. `ClerkSignInPanel` signs in with Clerk.
2. App uses the Clerk bearer token directly with Porterchain `/v1/*`.
3. `/v1/auth/me` resolves the principal and app session state.
4. Clerk owns bearer renewal; the customer app does not use Porterchain refresh tokens.

### Local Dev Fallback

`DevEmailSignInPanel` renders only when `EXPO_PUBLIC_APP_ENV=local`. It is intended to pair with API-side dev bypass settings for local development only.

---

## Transport Security

| Control | Status | Notes |
| ------- | ------ | ----- |
| Production HTTPS API URL | ✅ | EAS profiles point to `https://api.porterchain.com` |
| Driver 401 refresh | ✅ | `createSecureApiClient` retry path |
| Customer unauthorized handling | ✅ | Clears session and emits logout audit |
| Certificate pinning | ⚠ | Package support exists; enable after production pins are stable |
| WebSocket token handling | ⚠ | Notification WS still needs periodic review for token exposure |

---

## Local Data Protection

| Data | Storage | Protection |
| ---- | ------- | ---------- |
| Driver access/refresh tokens | Secure Store | OS keychain/keystore |
| Customer Clerk bearer | Secure Store | OS keychain/keystore |
| PIN hash | Secure Store | Salted SHA-256 |
| Offline queue | MMKV | Cache/replay only; not source of truth |
| Audit buffer | Encrypted MMKV | Encrypted local buffer |
| React Query cache | Memory | Cleared on app process end |

**Rule:** MMKV/offline data is never authoritative business state. Porterchain API remains source of truth.

---

## Device Controls

| Control | Status | Production Step |
| ------- | ------ | --------------- |
| PIN lock | ✅ | Confirm policy thresholds |
| Biometric unlock | ✅ | Test Face ID / Touch ID / Android biometric flows |
| Session timeout | ✅ | 15-minute idle policy |
| Device integrity | ⚠ | Register production adapter, such as a jailbreak/root detection library |
| Certificate pinning | ⚠ | Enable with production SHA-256 pins |

---

## Audit Events

Representative events:

- `login_success`, `logout`
- `session_timeout`
- `session_refresh`, `session_refresh_failed`
- `pin_set`, `pin_cleared`, `pin_failed`
- `biometric_unlock`
- `integrity_blocked`
- `pinning_mismatch`

Audit ingestion uses `POST /v1/security/audit-events` with sensitive fields scrubbed before persistence.

---

## Firebase / Push Security

| Item | Status | Notes |
| ---- | ------ | ----- |
| Permission before token | ✅ | Token fetched after permission flow |
| FCM token registration | ✅ | Driver and customer adapters call Porterchain API |
| Native credentials | ⚠ | Must be supplied via EAS secrets / secure credentials path |
| Push deep links | ✅ | Parsed and routed in-app |
| Secrets in JS bundle | ✅ | Firebase files are native config, not committed secrets |

---

## Findings Register

| ID | Severity | Finding | Status |
| -- | -------- | ------- | ------ |
| MS-001 | P0 | Dev auth fallback must not appear in production | ⚠ Require EAS/env guard verification |
| MS-002 | P0 | Firebase native credentials missing for release builds | ⚠ Open |
| MS-003 | P1 | Certificate pinning not enabled | ⚠ Open |
| MS-004 | P1 | Device integrity adapter not registered | ⚠ Open |
| MS-005 | P1 | No crash/security telemetry SDK | ⚠ Open |
| MS-006 | P2 | Offline replay needs penetration test | ⚠ Open |
| MS-007 | P2 | App privacy labels/runbook incomplete | ⚠ Open |

---

## Production Checklist

- [x] Clerk sign-in panel wired for both apps
- [x] Driver JWT refresh wired through secure API client
- [x] Secure token storage
- [x] PIN/biometric shell
- [x] Audit event emitter
- [ ] Verify production EAS profiles always set `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [ ] Verify local dev auth cannot render in production builds
- [ ] Supply Firebase native credentials securely
- [ ] Register device integrity adapter
- [ ] Enable certificate pinning after production cert/pin policy is stable
- [ ] Add crash reporting with PII scrubbing

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md) | Release readiness |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md) | Architecture |
| [MOBILE_UI_REPORT.md](./MOBILE_UI_REPORT.md) | UI coverage |
| [AUTHENTICATION.md](./AUTHENTICATION.md) | Platform auth |
| [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) | Env requirements |
