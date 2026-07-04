# Mobile Security Report

**Audit date:** June 30, 2026  
**Reference:** [masterrule.md](./masterrule.md) §15  
**Package:** `@porterchain/mobile-security` (`shared/mobile-security/`)

---

## Executive summary

Enterprise mobile security is **implemented** for both apps via a shared security layer. Production gaps are **Clerk sign-in completion**, **certificate pinning activation**, and **production integrity adapter** registration. Dev auth bypasses must be disabled in release builds.

**Security posture:** **Good foundation / needs production hardening**

---

## 1. Security capabilities matrix

| Capability | Status | Implementation |
|------------|--------|----------------|
| **Clerk** | ⚠️ Partial | `ClerkBridge` + `@clerk/clerk-expo` (dep added); email-only sign-in screens |
| **Secure Storage** | ✅ | `expo-secure-store` — tokens, PIN hash, session flags |
| **Biometric Login** | ✅ | `BiometricGate` + `expo-local-authentication` |
| **PIN Lock** | ✅ | `PinLockGate` + salted SHA-256 in secure store |
| **Certificate Pinning Ready** | ⚠️ Off | `configureCertificatePinning()` — `enableCertificatePinning: false` |
| **Jailbreak/Root Detection Ready** | ⚠️ Scaffold | `checkDeviceIntegrity()` + `registerIntegrityAdapter()` hook |
| **Session Timeout** | ✅ | 15 min idle via `AppState` |
| **Refresh Tokens** | ✅ Driver | `POST /driver-api/v1/auth/refresh` + auto-retry on 401 |
| **Encrypted Local Storage** | ✅ | MMKV key in Secure Store; audit buffer encrypted |
| **RBAC** | ✅ UI-only | `PermissionGate`, `principalFromAuthMe` — server enforces |
| **Audit Events** | ✅ | `POST /v1/security/audit-events` with PII scrubbing |

---

## 2. Provider architecture

```
ClerkBridge (optional ClerkProvider)
└── MobileSecurityProvider
    └── ApiProvider (createSecureApiClient)
        └── SecurityShell (on Main navigator)
            ├── IntegrityGate
            ├── BiometricGate
            └── PinLockGate
```

**Files:**
- `shared/mobile-security/src/provider/MobileSecurityProvider.tsx`
- `apps/mobile-*/src/providers/SecurityLayer.tsx`
- `apps/mobile-*/src/navigation/RootNavigator.tsx` — `SecurityShell` wraps `MainTabs`

---

## 3. Authentication flows

### Driver

1. User signs in → Clerk token (or dev `"dev"` fallback ⚠️)
2. `POST /driver-api/v1/auth/login` with `Authorization: Bearer {clerk}`
3. Server returns Porterchain `access_token` + `refresh_token`
4. Tokens stored in Secure Store via `auth-store` + `session-manager`
5. `createSecureApiClient` refreshes on 401

### Customer

1. User signs in → Clerk token (or dev path ⚠️)
2. Clerk JWT used as API bearer directly
3. `authMe()` resolves `user_id`, roles, permissions
4. No refresh token path (Clerk session manages renewal)

### Production gaps

| Gap | Risk | Fix |
|-----|------|-----|
| Dev token `"dev"` / `dev_clerk_user` | Critical in prod | Guard with `__DEV__` or `EXPO_PUBLIC_ALLOW_DEV_AUTH` |
| No Clerk SignIn UI | High | Wire `@clerk/clerk-expo` SignIn / OAuth |
| Customer raw Clerk JWT | Medium | Confirm API expects Clerk vs Porterchain JWT |

---

## 4. Transport security

| Control | Status |
|---------|--------|
| HTTPS only (prod API URL) | ✅ `https://api.porterchain.com` in EAS |
| Certificate pinning | ❌ Disabled |
| 401 → refresh (driver) | ✅ `createSecureApiClient` |
| Audit on logout | ✅ `emitSecurityEvent("sign_out")` |

**Pinning activation (when ready):**
```typescript
// SecurityLayer policy override
policy={{ enableCertificatePinning: true, certificatePins: ["sha256/..."] }}
```

---

## 5. Device integrity

| Check | Dev | Prod |
|-------|-----|------|
| Bundle ID allowlist | Skip | Basic check |
| Jailbreak/root libs | Skip | Requires `registerIntegrityAdapter()` (e.g. jail-monkey) |
| Simulator | Allowed | Configurable |

`IntegrityGate` blocks UI when `compromised === true`.

---

## 6. Local data protection

| Data | Storage | Encrypted |
|------|---------|-----------|
| Access / refresh tokens | Secure Store | OS keychain |
| PIN hash | Secure Store | Yes |
| Offline queue | MMKV | No (action metadata only) |
| Audit event buffer | Encrypted MMKV | Yes |
| React Query cache | Memory | N/A |

**Rule:** MMKV is cache/replay only — not authoritative business state (masterrule §2).

---

## 7. Audit events

**Emitted events:** `sign_in`, `sign_out`, `session_timeout`, `session_refresh`, `session_refresh_failed`, `pin_set`, `pin_cleared`, `pin_failed`, `biometric_unlock`, `integrity_blocked`, `pinning_mismatch`

**Ingestion:** `POST /v1/security/audit-events` — server strips `token`, `password`, `pin`, `secret` fields.

**Buffer:** Encrypted MMKV → flush every 60s + on foreground.

---

## 8. RBAC (client-side)

```typescript
<PermissionGate permission="orders:write">
  <Button label="Accept" />
</PermissionGate>
```

**Important:** Client RBAC is **UI-only**. All authorization enforced server-side on API routes.

---

## 9. Firebase / push security

| Item | Status |
|------|--------|
| FCM token over HTTPS register | ✅ |
| Permission before token | ✅ (audit fix) |
| Push payload deep links validated | ✅ parse only; navigate in-app |
| No secrets in mobile bundle | ✅ Firebase via native config files |

---

## 10. Remediation checklist

### Completed (this audit)

- [x] `@clerk/clerk-expo` added to app dependencies
- [x] Push permission before FCM token fetch
- [x] Removed duplicate `biometric.ts` (superseded by `mobile-security`)

### Required before production

- [ ] Clerk SignIn / OAuth screens
- [ ] Remove dev auth bypass in release builds
- [ ] EAS secret: `EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY`
- [ ] Register production integrity adapter
- [ ] Enable certificate pinning with production pins
- [ ] Sentry or crash SDK with PII scrubbing (masterrule §16)

### Recommended

- [ ] Penetration test on offline queue replay
- [ ] App Store privacy nutrition labels (location, camera, biometrics)
- [ ] Key rotation runbook for MMKV encryption key

---

## 11. Related documents

- [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md)
- [AUTHENTICATION.md](./AUTHENTICATION.md)
- [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)
