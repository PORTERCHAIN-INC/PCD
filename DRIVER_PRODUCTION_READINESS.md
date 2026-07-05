# Driver Portal — Production Readiness Report


**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Scope:** `apps/driver-portal/`, `apps/mobile-driver/`, `/driver-api/v1/*`, `services/driver-platform/`

> **Platform status:** Overall Porterchain is **NOT production ready** — [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md). This report covers **driver surfaces only**.

---

## Executive summary

| Dimension | Score | Verdict |
| --------- | ----- | ------- |
| Architecture compliance | 95% | ✅ No Fleetbase / business API bypass |
| Backend API surface | 92% | ✅ ~75 route handlers on `driver.py` |
| Driver web portal | 85% | ✅ Jobs, navigation, POD, comms, shift |
| Mobile driver app | 70% | ⚠ Execution flows wired; EAS/Firebase ops gaps |
| Security | 80% | ✅ Middleware + OTP fixes; refresh BFF partial |
| Offline / resilience | 80% | ✅ Queue, GPS buffer, sync executor |
| Realtime | 65% | ⚠ Notifications WS; jobs poll-based |

**Web pilot:** ✅ Suitable for **controlled pilot** when `FLEETBASE_DISPATCH_BRIDGE=true`, Maps key, and approved drivers.

**Mobile + full rollout:** ⚠ Complete Firebase production creds, EAS deploy, and refresh-token UX before wide production.

---

## Module verification matrix

| Module | Surface | Backend | Web portal | Mobile | Status |
| ------ | ------- | ------- | ---------- | ------ | ------ |
| Dashboard | `/dashboard` | ✅ | ✅ | ✅ Home | ✅ |
| Jobs / Delivery 360 | `/jobs`, `/jobs/[orderId]` | ✅ | ✅ | ✅ Jobs stack | ✅ |
| Navigation | `/navigation` | ✅ | ✅ + `@porterchain/maps` | ✅ + `@porterchain/mobile-maps` | ✅* |
| GPS | Nav + offline | ✅ | ✅ | ✅ `expo-location` | ✅ |
| Shift | `/shift` | ✅ | ✅ | ✅ ShiftScreen | ✅ |
| POD | Job detail | ✅ | ✅ | ✅ PodScreen | ✅ |
| Communications | `/communications` | ✅ | ✅ | ✅ Notifications | ✅ |
| Earnings / wallet | `/earnings`, `/wallet` | ✅ | ✅ | ✅ Earnings | ✅ |
| Support / claims / SOS | `/support`, `/emergency` | ✅ | ✅ | ✅ Support/SOS | ✅ |
| Push (FCM) | Device register | ✅ | ⚠ synthetic web token | ✅ `/push/register` | ⚠ |
| Offline sync | Global | ✅ | ✅ offline-client | ✅ OfflineSync | ✅ |
| RBAC | Approved gate | ✅ | ✅ middleware | ✅ Clerk + JWT | ⚠ thin role |

\* Requires `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` / mobile maps config.

---

## Architecture compliance

```
Driver Portal (:3003) / Mobile Driver (Expo)
    ↓ HTTPS — BFF /api/driver/* (web) or direct :8001 (mobile)
Porterchain API (:8001) — /driver-api/v1/*
    ↓
porterchain_driver/* + driver_engine/*
    ↓ PostgreSQL 16
DriverFleetbaseBridge → fleetbase-adapter → Fleetbase (:8000)
```

| Rule | Status |
| ---- | ------ |
| UI → Porterchain API only | ✅ |
| Business logic in services | ✅ |
| Fleetbase via adapter only | ✅ |
| Finance via billing_engine | ✅ |
| Notifications via notification_engine | ✅ |

Production: `PortalRateLimitMiddleware` on `/driver-api/*` (skipped in `local`).

---

## Gaps fixed (2026-06/07 audit cycle)

| Gap | Fix |
| --- | --- |
| Accept/reject Fleetbase sync | `availability.py` + bridge |
| OTP authorization hole | Assigned-driver check on `generate_otp` |
| POD/exception approval gate | `require_approved_driver` |
| Stop → Fleetbase sync | `StopsService` + bridge |
| Next.js route protection | ✅ `apps/driver-portal/src/middleware.ts` |
| Mobile Clerk auth | ✅ `ClerkSignInPanel` + token exchange |
| Mobile execution screens | Jobs, POD, navigation, offline sync |

---

## Remaining blockers

### P0 — Before wide rollout

| Item | Status | Recommendation |
| ---- | ------ | -------------- |
| JWT refresh BFF route | ⚠ | Wire `POST /driver-api/v1/auth/refresh` in portal BFF + mobile client |
| Firebase web FCM | ⚠ | FCM SDK or document mobile-only push |
| Platform production cert | Open | [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) |

### P1 — Quality / ops

| Item | Impact |
| ---- | ------ |
| WebSocket via BFF proxy | Token in WS URL |
| Synthetic `route-{date}` IDs | Fleetbase route binding |
| Earnings helper hardcoded cents | Wire to pricing_engine |
| Emergency rate limit | SOS abuse prevention |

---

## Environment checklist

| Variable | Purpose |
| -------- | ------- |
| `NEXT_PUBLIC_PORTERCHAIN_API_URL` | BFF → API `:8001` |
| `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY` | Navigation maps |
| `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` | Login (web + mobile) |
| `FLEETBASE_DISPATCH_BRIDGE=true` | Execution sync |
| Firebase credentials | Push delivery |
| `DATABASE_URL` | PostgreSQL 16 |

See [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md) · [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md).

---

## Verdict

**Web driver portal:** Approved for **controlled pilot** with documented limitations (web FCM, polling job updates).

**Mobile driver:** Suitable for **internal/beta** with Clerk + execution flows; complete ops checklist before store release.

---

## Related

| Document | Purpose |
| -------- | ------- |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md) | Platform design |
| [docs/architecture/DISPATCH_FLOW.md](./docs/architecture/DISPATCH_FLOW.md) | Dispatch flow |
| [docs/archive/DRIVER_AUDIT.md](./docs/archive/DRIVER_AUDIT.md) | Historical architecture audit |
---

## Governance

| Document | Role |
| -------- | ---- |
| [masterrule.md](masterrule.md) | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
