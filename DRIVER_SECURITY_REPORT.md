# Driver Platform — Security Report

**Reference:** [masterrule.md](./masterrule.md) §15  
**Date:** June 30, 2026

---

## Executive summary

| Area | Rating | Notes |
|------|--------|-------|
| Transport security | ✅ | HTTPS assumed in production |
| Authentication | ⚠ | JWT in httpOnly cookies; no refresh flow |
| Authorization (RBAC) | ⚠ | Binary approved-driver gate |
| API boundary | ✅ | No Fleetbase/direct business API leakage |
| Data isolation | ✅ | Driver context scoped to own records |
| Secrets in client | ✅ | No API secrets in portal bundle |
| WebSocket auth | ⚠ | Short-lived token via `/api/auth/ws-token` |
| Input validation | ✅ | Pydantic schemas on API |
| Offline queue | ⚠ | localStorage — device compromise risk |

**Overall:** Acceptable for **pilot** with approved drivers. Address P0 items before public production.

---

## 1. Authentication

### Web driver portal

| Control | Implementation | Status |
|---------|----------------|--------|
| Login | Clerk exchange or dev email → `POST /driver-api/v1/auth/login` | ✅ |
| Token storage | `driver_access_token` httpOnly cookie | ✅ |
| Refresh token | `driver_refresh_token` cookie stored | ⚠ No refresh endpoint used |
| Session check | `GET /api/auth/session` | ✅ |
| Client guard | `hasDriverSession()` per page | ⚠ Client-only |
| Server middleware | — | ❌ Missing |

**Risk:** Protected pages may flash before client redirect. **Mitigation:** Add Next.js `middleware.ts` checking `driver_access_token`.

### API driver context

| Control | Implementation |
|---------|----------------|
| JWT validation | `auth/driver.py` — Bearer from Authorization header |
| Dev bypass | `x_driver_id` header / first approved driver (dev only) |
| Suspended drivers | 403 `driver_suspended` |

---

## 2. Authorization (RBAC)

### Model

```
DriverStatus: pending | approved | suspended
require_approved_driver(ctx) → 403 if not approved
```

### Endpoints with approval gate

Shift lifecycle, availability, location, route start, arrive/deliver, accept/reject, offline sync/retry, POD endpoints, stop exception, OTP generation.

### Endpoints without approval gate (by design)

| Endpoint | Rationale |
|----------|-----------|
| `GET /profile`, `/documents` | Onboarding — pending drivers upload docs |
| `POST /documents` | Compliance upload while pending |
| `POST /support`, `/incidents` | Report issues while pending |
| `POST /offline/queue` | Queue while pending (sync requires approval) |

### Vulnerabilities patched (this audit)

| Issue | Severity | Fix |
|-------|----------|-----|
| OTP for any order | **High** | `generate_otp` requires `assigned_driver_id == driver.id` |
| Reject without approval | Medium | `require_approved_driver` on reject |
| POD without approval | Medium | `require_approved_driver` on all POD endpoints |

### Remaining authorization gaps

| Issue | Severity | Recommendation |
|-------|----------|----------------|
| No granular scopes | Low | Acceptable per masterrule single-driver role |
| Document upload while suspended | Medium | Block at auth layer for suspended |
| No order-level audit log in UI | Low | Admin portal concern |

---

## 3. API boundary security

### Verified: no forbidden calls from driver portal

```
✅ No fetch to :8000 (Fleetbase)
✅ No fetch to /merchant-api or /admin-api
✅ All data via /api/driver BFF
✅ Login server-side only
```

### Exception: WebSocket

```
Client → ws://{API}/v1/notifications/ws?token={bearer}
Token from GET /api/auth/ws-token (reads httpOnly cookie server-side)
```

| Risk | Mitigation |
|------|------------|
| Token in WS URL (logs, referrer) | Short-lived JWT; same-origin policy |
| Direct API exposure | Consider BFF WebSocket proxy |

---

## 4. Data protection

| Data type | Storage | Exposure |
|-----------|---------|----------|
| JWT | httpOnly cookie | Not accessible to JS |
| Offline queue | localStorage | Device-local; no secrets |
| GPS buffer | localStorage | Coordinates only |
| POD URLs | Queued as URLs | User-supplied; validate server-side |
| OTP hash | `DriverStopMeta` server | Plain OTP returned once to assigned driver |

### PII in driver portal

- Customer name/phone on job detail — **required for delivery**
- Merchant info — **required for pickup**
- Earnings — **driver's own data only**

---

## 5. Fleetbase boundary

| Rule | Status |
|------|--------|
| No Fleetbase credentials in UI | ✅ |
| No Fleetbase URLs in client | ✅ |
| Bridge gated by env flag | ✅ |
| Adapter is sole HTTP boundary | ✅ |

Driver cannot invoke Fleetbase admin APIs or bypass Porterchain order ownership checks (except patched OTP hole).

---

## 6. Push / Firebase security

| Control | Status |
|---------|--------|
| FCM server key | Server-only (`settings`) |
| Device registration | Requires authenticated driver |
| Web push token | Synthetic `web-{uuid}` — not cryptographically bound to FCM |
| Permission prompt | Browser `Notification.requestPermission()` |

**Risk:** Web push registration is placeholder until FCM SDK integrated.

---

## 7. Emergency / SOS

| Control | Implementation |
|---------|----------------|
| Auth required | ✅ Session guard on `/emergency` |
| Rate limiting | ❌ Not implemented |
| GPS optional | Alert sent without location if denied |
| Admin notification | `driver.emergency` → admin in_app critical |

**Recommendation:** Add rate limit on `POST /emergency` (e.g. 3/hour/driver).

---

## 8. Offline sync security

| Control | Status |
|---------|--------|
| Queue replay auth | Requires valid JWT on sync |
| Action ownership | `DriverOfflineAction.driver_id` scoped |
| Executor sandbox | Only whitelisted action types |
| Idempotency | ❌ No client_id dedup on server |

**Risk:** Replay of queued actions if token stolen. **Mitigation:** Short JWT TTL + refresh (future).

---

## 9. Compliance checklist (masterrule §15)

| Requirement | Status |
|-------------|--------|
| Auth on all mutations | ✅ |
| No secrets in frontend | ✅ |
| Fleetbase adapter only | ✅ |
| Driver sees own data only | ✅ (with OTP fix) |
| Suspended driver blocked | ✅ |
| Audit events emitted | ✅ Domain events on state changes |
| HTTPS in production | ⚠ Deploy config |

---

## 10. Remediation priority

### P0 (before production)

1. Add Next.js middleware for route protection
2. ~~OTP authorization~~ ✅ Fixed
3. Rate limit emergency endpoint

### P1

4. JWT refresh flow
5. WebSocket BFF proxy
6. Server-side dedup for offline queue (`client_id`)

### P2

7. True FCM web integration
8. Block document upload for suspended drivers
9. Security headers on driver-portal (CSP, HSTS via deploy)

---

## 11. Verdict

Driver platform security is **aligned with masterrule** for architecture boundaries. Authentication is adequate for pilot. **Critical OTP vulnerability is resolved.** Primary remaining risks are client-only route guards, WebSocket token handling, and lack of rate limiting on SOS.
