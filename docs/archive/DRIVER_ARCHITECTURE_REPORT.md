# Driver Platform — Architecture Report

**Last verified:** 2026-07-04  
**Scope:** Driver domain across API, services, web portal, and mobile

> **Canonical platform doc:** [DRIVER_PLATFORM.md](./DRIVER_PLATFORM.md)  
> **Audit:** [DRIVER_AUDIT.md](./DRIVER_AUDIT.md)

---

## Overview

The driver domain spans four layers:

```
┌─────────────────────────────────────────────────────────┐
│  Clients: driver-portal (:3003) · mobile-driver (Expo)  │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼─────────────────────────────┐
│  Porterchain API (:8001) — routers/driver.py            │
│  Prefix: /driver-api/v1/*                               │
└───────────────────────────┬─────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
 porterchain_driver    driver_engine      notification_engine
 (services/driver-      (auth, bridge,     (DeviceService,
  platform/)             offline exec)       push register)
        │                   │
        └─────────┬─────────┘
                  ▼
         PostgreSQL 16 (drivers, orders, pings, offline queue)
                  │
                  ▼
         fleetbase-adapter → Fleetbase API (:8000)
```

---

## Component map

| Component       | Location                                         | Responsibility                   |
| --------------- | ------------------------------------------------ | -------------------------------- |
| REST surface    | `apps/api/src/porterchain_api/routers/driver.py` | ~75 handlers                     |
| Domain services | `services/driver-platform/porterchain_driver/`   | Reusable driver logic            |
| Engine          | `apps/api/.../driver_engine/`                    | JWT auth, Fleetbase bridge, RBAC |
| Web BFF         | `apps/driver-portal/src/app/api/`                | Cookie session, driver proxy     |
| Web UI          | `apps/driver-portal/src/app/`                    | Dashboard, jobs, nav, POD        |
| Mobile          | `apps/mobile-driver/src/`                        | Execution-first Expo app         |
| Adapter         | `services/fleetbase-adapter/`                    | Fleetbase sync only              |

---

## Authentication flow

```
Clerk (web/mobile login)
    → POST /driver-api/v1/auth/login { email, clerkToken }
    → Porterchain JWT (access + refresh)

Web: BFF sets httpOnly cookies (driver_access_token, driver_refresh_token)
Mobile: secure storage via auth-store

Protected routes: Bearer JWT or BFF cookie → require_approved_driver
```

Refresh: `POST /driver-api/v1/auth/refresh` on API — **BFF refresh route not yet wired** (July 2026).

Dev: `CLERK_DEV_BYPASS` + `APP_ENV=local` allows simplified login paths.

---

## Request path (web)

```
Browser → driver-portal :3003
    → middleware.ts (cookie guard, public /login + /api/auth/*)
    → /api/driver/[...path] BFF → :8001/driver-api/v1/*
    → porterchain_driver services → PostgreSQL
    → DriverFleetbaseBridge (when bridge enabled) → Fleetbase
```

Production: `PortalRateLimitMiddleware` applies to `/driver-api/` paths.

---

## Request path (mobile)

```
Expo app → :8001/driver-api/v1/* (direct)
    → same services + bridge
    → offline queue when disconnected → sync on reconnect
```

Maps: `@porterchain/mobile-maps` + `expo-location` for navigation and GPS pings.

---

## Key services (`porterchain_driver`)

| Service               | Primary endpoints               | Fleetbase touch        |
| --------------------- | ------------------------------- | ---------------------- |
| `DashboardService`    | `GET /dashboard`                | —                      |
| `JobsService`         | routes, orders                  | bridge on state change |
| `StopsService`        | arrive, deliver, exceptions     | sync stops             |
| `NavigationService`   | polyline, ETA                   | routing via adapter    |
| `PodService`          | OTP, photo, signature, complete | upload proof           |
| `LocationService`     | `POST /location`                | track ping             |
| `ShiftService`        | shift lifecycle                 | —                      |
| `AvailabilityService` | accept/reject, online           | dispatch bridge        |
| `OfflineService`      | queue, sync                     | replay actions         |
| `PushService`         | register                        | → DeviceService        |

---

## Data stores

| Store                | Tables / usage                                                                                                           |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| PostgreSQL 16        | `drivers`, `orders`, `driver_wallet_transactions`, `driver_location_pings`, `driver_offline_actions`, `driver_stop_meta` |
| Notification devices | `notification_devices` via push register                                                                                 |
| Fleetbase            | Orders, routes, tracking (via adapter)                                                                                   |

Alembic head: `n2o3p4q5r6s7` (13 revisions).

---

## Events emitted

Driver actions emit domain events through `event_router`:

- Assignment: `order.driver_accepted`, `order.driver_rejected`
- Execution: pickup/delivery lifecycle, `order.pod_completed`
- Ops: `driver.emergency`, shift events, `driver.route_changed`
- Notifications: `notification.queued`

See [EVENT_CATALOG.md](./EVENT_CATALOG.md).

---

## UI coverage (July 2026)

| Surface     | Maturity | Notes                                         |
| ----------- | -------- | --------------------------------------------- |
| Web portal  | ~85%     | Jobs, navigation, POD, comms, shift           |
| Mobile      | ~70%     | Full execution; ops gaps (EAS, Firebase prod) |
| Backend API | ~92%     | Refresh endpoint exists; some synthetic IDs   |

---

## Known limitations

1. **Refresh UX** — API supports refresh; portal BFF and mobile auto-refresh incomplete.
2. **Web push** — Synthetic token path; production FCM policy TBD.
3. **WebSocket auth** — Token passed in query string via ws-token route.
4. **Route IDs** — Some synthetic `route-{date}` bindings until Fleetbase route linkage hardened.
5. **Platform readiness** — Driver pilot OK; full production blocked by [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md).

---

## Related

| Document                                                                               | Purpose          |
| -------------------------------------------------------------------------------------- | ---------------- |
| [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md)                     | Pilot checklist  |
| [DRIVER_SECURITY_REPORT.md](./DRIVER_SECURITY_REPORT.md)                               | Security posture |
| [PORT_CONFIGURATION.md](./PORT_CONFIGURATION.md)                                       | Port 3003 / 8001 |
| [docs/architecture/AUTHENTICATION_FLOW.md](./docs/architecture/AUTHENTICATION_FLOW.md) | Clerk + JWT      |
