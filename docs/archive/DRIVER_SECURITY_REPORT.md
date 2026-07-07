# Driver Platform — Security Report

**Last verified:** 2026-07-04  
**Scope:** `apps/driver-portal/`, `apps/mobile-driver/`, `/driver-api/v1/*`, `driver_engine/`

> **See also:** [DRIVER_AUDIT.md](./DRIVER_AUDIT.md) · [SECURITY.md](./SECURITY.md) · [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md)

---

## Executive summary

| Area                       | Posture   | Notes                                          |
| -------------------------- | --------- | ---------------------------------------------- |
| Auth (Clerk → JWT)         | ✅ Strong | Single identity path; dev bypass gated         |
| Token storage (web)        | ✅ Strong | httpOnly cookies via BFF                       |
| Token storage (mobile)     | ✅ Strong | Secure storage (`auth-store`)                  |
| Route protection (web)     | ✅ Fixed  | `middleware.ts` cookie guard                   |
| API authorization          | ✅ Good   | `require_approved_driver`; OTP/POD gates fixed |
| Fleetbase isolation        | ✅ Strong | Adapter-only; no UI direct access              |
| Rate limiting              | ✅ Prod   | `PortalRateLimitMiddleware` on `/driver-api/`  |
| Refresh / session rotation | ⚠ Partial | API endpoint exists; client wiring incomplete  |
| WebSocket auth             | ⚠ Weak    | Token in query string                          |
| Push (web)                 | ⚠ Weak    | Synthetic FCM token path                       |
| RBAC depth                 | ⚠ Thin    | Approved-driver gate only                      |

**Overall:** Suitable for **controlled pilot**. Address refresh UX and WS auth before wide production.

---

## Authentication

### Flow

1. User signs in with **Clerk** (web portal or mobile).
2. Client sends Clerk bearer to `POST /driver-api/v1/auth/login` with driver email.
3. API returns Porterchain **access + refresh** JWT pair.
4. **Web:** BFF (`/api/auth/login`) sets `driver_access_token` and `driver_refresh_token` as **httpOnly**, `sameSite=lax`, `secure` in production.
5. **Mobile:** Tokens stored via secure storage; Clerk session separate.

### Dev bypass

When `CLERK_DEV_BYPASS=true` and `APP_ENV=local`, simplified paths (email-only / `X-Driver-Id`) are allowed. **Must remain disabled in production.**

---

## Web portal security

| Control         | Status       | Implementation                                                                       |
| --------------- | ------------ | ------------------------------------------------------------------------------------ |
| Route guard     | ✅           | `apps/driver-portal/src/middleware.ts` — redirects unauthenticated users to `/login` |
| Public paths    | ✅           | `/login`, `/api/auth/login`, `/api/auth/driver-session`                              |
| API BFF         | ✅           | `/api/driver/[...path]` — server-side proxy with cookie auth                         |
| XSS token theft | ✅ Mitigated | JWT not in `localStorage`                                                            |
| CSRF            | ⚠            | SameSite=lax cookies; no explicit CSRF token on mutations                            |
| Clerk scope     | ✅           | Clerk only at login; Porterchain JWT for API                                         |

### Middleware (July 2026 — resolved)

```typescript
// apps/driver-portal/src/middleware.ts
// Checks driver_access_token cookie; public prefixes exempt
```

Previously flagged **P0** in June audit — **now implemented**.

---

## Mobile security

| Control                  | Status | Implementation                                      |
| ------------------------ | ------ | --------------------------------------------------- |
| Clerk production auth    | ✅     | `ClerkSignInPanel` + `@porterchain/mobile-security` |
| Token storage            | ✅     | Secure storage keys for access/refresh              |
| API transport            | ✅     | HTTPS to Porterchain API only                       |
| Certificate pinning      | ❌     | Not implemented                                     |
| Jailbreak/root detection | ❌     | Not implemented                                     |

---

## API security (`/driver-api/v1`)

| Control              | Status   | Notes                                          |
| -------------------- | -------- | ---------------------------------------------- |
| JWT validation       | ✅       | Bearer on protected routes                     |
| Approved driver gate | ✅       | `require_approved_driver`                      |
| OTP generation       | ✅ Fixed | Assigned-driver check                          |
| POD endpoints        | ✅ Fixed | Approval gate on sensitive actions             |
| Auth refresh         | ✅ API   | `POST /auth/refresh` — clients partially wired |
| Rate limiting        | ✅ Prod  | Portal rate limit middleware                   |
| Emergency SOS        | ⚠        | No dedicated rate limit                        |
| Legacy push route    | ✅       | Delegates to `DeviceService` with validation   |

---

## Findings register

| ID     | Severity | Finding                          | Status                                           |
| ------ | -------- | -------------------------------- | ------------------------------------------------ |
| DS-001 | P0       | No Next.js middleware            | ✅ **Resolved** — `middleware.ts`                |
| DS-002 | P0       | OTP without driver authorization | ✅ **Resolved**                                  |
| DS-003 | P0       | POD without approval gate        | ✅ **Resolved**                                  |
| DS-004 | P1       | JWT in localStorage (portal)     | ✅ **Resolved** — httpOnly cookies               |
| DS-005 | P1       | No refresh token rotation UX     | ⚠ **Open** — API ready; add BFF + mobile refresh |
| DS-006 | P1       | Mobile lacks Clerk               | ✅ **Resolved**                                  |
| DS-007 | P2       | WS token in URL query            | ⚠ **Open** — `/api/auth/ws-token`                |
| DS-008 | P2       | Thin RBAC (approved only)        | ⚠ **Open**                                       |
| DS-009 | P2       | Web FCM synthetic token          | ⚠ **Open**                                       |
| DS-010 | P2       | Emergency endpoint abuse         | ⚠ **Open** — add rate limit                      |

---

## Token lifecycle gaps

| Client     | Access token    | Refresh token                | Gap                                         |
| ---------- | --------------- | ---------------------------- | ------------------------------------------- |
| Web portal | httpOnly cookie | httpOnly cookie set at login | No BFF route calling `/auth/refresh` on 401 |
| Mobile     | Secure storage  | Secure storage               | No automatic refresh before expiry          |

**Recommendation:** Add `/api/auth/refresh` BFF route; mobile client interceptor on 401 → refresh → retry.

---

## Fleetbase and data isolation

| Rule                                | Status                         |
| ----------------------------------- | ------------------------------ |
| No Fleetbase credentials in clients | ✅                             |
| No direct Fleetbase HTTP from UI    | ✅                             |
| Bridge gated by env flag            | ✅ `FLEETBASE_DISPATCH_BRIDGE` |
| Driver PII in Porterchain DB        | ✅ PostgreSQL 16               |

---

## Production checklist (driver-specific)

- [x] Next.js middleware for session guard
- [x] httpOnly cookie JWT storage (web)
- [x] Clerk on mobile
- [x] OTP/POD authorization fixes
- [ ] Refresh token rotation (web + mobile)
- [ ] WebSocket auth without query token
- [ ] Production Firebase credentials (mobile push)
- [ ] Emergency endpoint rate limit
- [ ] Platform-wide gates — [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md)

---

## Related

| Document                                                           | Purpose          |
| ------------------------------------------------------------------ | ---------------- |
| [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md) | Readiness matrix |
| [RBAC.md](./RBAC.md)                                               | Platform RBAC    |
| [AUTHENTICATION.md](./AUTHENTICATION.md)                           | Auth overview    |
