# Driver Platform — Architecture Audit

**Last verified:** 2026-07-04  
**Scope:** `services/driver-platform/`, `apps/api/.../driver_engine/`, `apps/driver-portal/`, `apps/mobile-driver/`, `/driver-api/v1/*`  
**Baseline:** June 2026 audit · **July 2026 reconciliation** below

> **See also:** [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md) · [DRIVER_SECURITY_REPORT.md](./DRIVER_SECURITY_REPORT.md)

---

## Executive summary

| Dimension | June 2026 | July 2026 |
| --------- | --------- | ---------- |
| Backend API | ~92% | ~92% (~75 handlers) |
| Driver web portal | ~39% (read-only) | **~85%** (jobs, nav, POD, comms) |
| Mobile driver | ~12% (auth only) | **~70%** (execution flows + Clerk) |
| Security posture | 65% | **~80%** (middleware, OTP fixes) |
| Architecture compliance | 95% | **95%** |

**Verdict:** Backend and architecture remain strong. **Web and mobile UIs have caught up materially** since the June audit; remaining gaps are ops (Firebase/EAS), refresh-token UX, and platform-wide production certification.

---

## 1. Architecture compliance

| Rule | Status | Evidence |
| ---- | ------ | -------- |
| UI → Porterchain API only | ✅ | BFF `/api/driver/*`; mobile direct `:8001` |
| No Fleetbase from UI | ✅ | Adapter + bridge only |
| Business logic in services | ✅ | `porterchain_driver/*` |
| Finance via billing_engine | ✅ | `earnings.py`, `finance.py` |
| Notifications via notification_engine | ✅ | `DeviceService`, `communications.py` |
| Events via event_router | ✅ | `emit_event` in driver_engine |

---

## 2. Backend API (`driver.py`)

**Coverage:** ~75 route handlers across auth, dashboard, jobs, routes/stops, POD, location, shift, offline, support, push, emergency.

| Area | Status | Notes |
| ---- | ------ | ----- |
| Auth login + refresh | ✅ | `POST /auth/login`, `POST /auth/refresh` |
| Job accept/reject | ✅ | Fleetbase bridge on accept |
| Stop execution | ✅ | arrive, deliver, exceptions |
| POD | ✅ | OTP gate fixed (assigned driver only) |
| GPS | ✅ | DB + Fleetbase track |
| Offline queue | ✅ | queue, pending, sync executor |
| Push register | ✅ | Delegates to `DeviceService` |
| Rate limiting | ✅ | `PortalRateLimitMiddleware` on `/driver-api/` (prod) |

**Known backend gaps:** Synthetic route IDs in some paths; earnings cents hardcoded in helper; emergency endpoint lacks dedicated rate limit.

---

## 3. Driver web portal (`apps/driver-portal/`)

> **June audit was stale** — portal is no longer read-only.

| Feature | Route / component | API wired | Status |
| ------- | ----------------- | --------- | ------ |
| Login (Clerk → JWT) | `/login`, BFF `/api/auth/login` | ✅ | ✅ |
| Session guard | `middleware.ts` | httpOnly cookie | ✅ |
| Dashboard | `/` | `/dashboard` | ✅ |
| Jobs list + detail | `/jobs`, `/jobs/[orderId]` | routes, orders | ✅ |
| Navigation | `/navigation` | `@porterchain/maps` | ✅* |
| Shift | `/shift` | `/shift/*` | ✅ |
| Communications | `/communications` | notifications hub | ✅ |
| Earnings / wallet | `/earnings`, `/wallet` | earnings API | ✅ |
| Profile / onboarding | `/profile` | `/profile`, `/onboarding` | ✅ |
| Support / emergency | `/support`, `/emergency` | support, SOS | ✅ |
| BFF proxy | `/api/driver/[...path]` | all driver-api | ✅ |
| WebSocket token | `/api/auth/ws-token` | WS auth | ⚠ token in URL |
| Push (web FCM) | profile/settings | synthetic token path | ⚠ |

\* Maps require `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`.

**Estimated API coverage (portal UI):** ~85% of driver-api surface used in primary flows.

---

## 4. Mobile driver (`apps/mobile-driver/`)

> **June audit listed ~12% coverage (auth only)** — July 2026 includes full execution stack.

| Screen / flow | Status | API |
| ------------- | ------ | --- |
| Clerk sign-in | ✅ | `/auth/login` + secure token store |
| Home dashboard | ✅ | `/dashboard` |
| Jobs (list, detail, accept/reject) | ✅ | orders, routes |
| Navigation + GPS | ✅ | `@porterchain/mobile-maps`, `expo-location`, `/location` |
| POD (OTP, photo, signature) | ✅ | pod-* endpoints |
| Shift | ✅ | `/shift/*`, availability |
| Earnings | ✅ | earnings |
| Offline sync | ✅ | offline queue + sync |
| Push register | ✅ | `/push/register` |
| Support / SOS | ✅ | support, `/emergency` |

**Estimated API coverage (mobile UI):** ~70% — core execution complete; refresh-token rotation and production Firebase/EAS ops remain.

---

## 5. Security findings

| ID | Finding | June | July |
| -- | ------- | ---- | ---- |
| AV-D01 | No Next.js middleware | 🔴 P0 | ✅ Fixed — `middleware.ts` |
| AV-D02 | OTP without driver check | 🔴 P0 | ✅ Fixed |
| AV-D03 | POD without approval gate | 🔴 P0 | ✅ Fixed |
| AV-D04 | JWT in localStorage (portal) | 🟡 | ✅ httpOnly cookies via BFF |
| AV-D05 | No auth refresh UX | 🟡 | ⚠ API exists; BFF/mobile client partial |
| AV-D06 | Mobile no Clerk | 🟡 | ✅ `ClerkSignInPanel` |
| AV-D07 | WS token in query string | 🟡 | Open |
| AV-D08 | Thin RBAC (approved only) | 🟡 | Open |

Detail: [DRIVER_SECURITY_REPORT.md](./DRIVER_SECURITY_REPORT.md).

---

## 6. Fleetbase integration

| Sync point | Status |
| ---------- | ------ |
| Accept order → dispatch | ✅ bridge |
| GPS track | ✅ adapter |
| Stop arrive/deliver | ✅ `StopsService` + bridge |
| POD upload | ✅ adapter |
| Online/offline toggle | ✅ availability |

Gated by `FLEETBASE_DISPATCH_BRIDGE=true`.

---

## 7. Offline and resilience

| Capability | Web | Mobile |
| ---------- | --- | ------ |
| Action queue | ✅ offline-client | ✅ MMKV queue |
| Sync executor | ✅ API-side | ✅ `/offline/sync` |
| GPS buffer | ✅ | ✅ location service |

---

## 8. Recommendations (priority)

| Priority | Item |
| -------- | ---- |
| P0 | Wire refresh flow: BFF route + mobile auto-refresh before expiry |
| P0 | Platform production checklist — [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) |
| P1 | Production Firebase + EAS for mobile push |
| P1 | Web FCM or document mobile-only push policy |
| P2 | WS auth via header/cookie proxy |
| P2 | Emergency endpoint rate limit |

---

## 9. Related documents

| Document | Purpose |
| -------- | ------- |
| [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md) | Platform design |
| [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md) | Pilot readiness |
| [CONNECTIONS.md](./CONNECTIONS.md) | Mobile API contract |
| [docs/architecture/DISPATCH_FLOW.md](./docs/architecture/DISPATCH_FLOW.md) | Dispatch integration |
