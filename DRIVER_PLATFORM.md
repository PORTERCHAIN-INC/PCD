# Porterchain Driver Platform

**Type:** CANONICAL
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

**Package:** `services/driver-platform` (`porterchain-driver` / `porterchain_driver`)

> **See also:** [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md) · [docs/architecture/DISPATCH_FLOW.md](./docs/architecture/DISPATCH_FLOW.md)

---

## Purpose

The Porterchain Driver Platform **extends Fleetbase** — it does not replace it. Fleetbase owns logistics execution (dispatch, GPS, routing). Porterchain owns the driver experience: earnings, wallet, compliance, POD capture, training, and support.

```
Driver App / Portal (:3003)
        │
        ▼
/driver-api/v1/*  (Porterchain API :8001)
        │
        ├── porterchain_driver (reusable services)
        ├── driver_engine (auth, bridge, offline executor)
        │
        └── Fleetbase Adapter (sync only)
                │
                ▼
            Fleetbase API (:8000)
```

---

## Architecture

| Layer             | Path                                           | Role                                    |
| ----------------- | ---------------------------------------------- | --------------------------------------- |
| Reusable services | `services/driver-platform/porterchain_driver/` | Business logic                          |
| API engine        | `apps/api/.../driver_engine/`                  | Auth, Fleetbase bridge, RBAC            |
| API routes        | `apps/api/.../routers/driver.py`               | `/driver-api/v1/*` REST (~75 handlers)  |
| Web portal        | `apps/driver-portal/`                          | Next.js BFF + dashboard (port **3003**) |
| Mobile            | `apps/mobile-driver/`                          | Expo — same API, execution-first        |
| Fleetbase         | `services/fleetbase-adapter/`                  | track, toggle-online, POD, routes       |

---

## DriverPlatform services

| Service            | Module                      | Capabilities                       |
| ------------------ | --------------------------- | ---------------------------------- |
| Dashboard          | `dashboard.py`              | Today's earnings, stops, wallet    |
| Jobs               | `jobs.py`                   | Job list, detail, history          |
| Stops              | `stops.py`                  | Route, arrive, deliver, exceptions |
| Navigation         | `navigation.py`             | Polyline, ETA via Fleetbase + maps |
| Shift              | `shift.py`                  | Shift lifecycle                    |
| Availability       | `availability.py`           | Online/offline, accept/reject      |
| POD                | `pod.py`                    | OTP, photo, signature, complete    |
| Location           | `location.py`               | GPS → DB + Fleetbase track         |
| Earnings / finance | `earnings.py`, `finance.py` | billing_engine delegation          |
| Communications     | `communications.py`         | Notification hub                   |
| Offline            | `offline.py`                | Queue + sync                       |
| Push               | `push.py`                   | → `DeviceService`                  |
| Emergency          | `emergency.py`              | Distress → ops + event             |

```python
from porterchain_driver import DriverPlatform

platform = DriverPlatform()
snap = platform.dashboard.snapshot(db, driver)
```

---

## API (`/driver-api/v1`)

| Area                 | Endpoints (representative)                                              |
| -------------------- | ----------------------------------------------------------------------- |
| Auth                 | `POST /auth/login`, `POST /auth/refresh`, `GET /me`                     |
| Workspace            | `GET /dashboard`, `/onboarding`, `/profile`                             |
| Jobs / routes        | `GET /routes/assigned`, `POST /routes/{id}/start`, stops arrive/deliver |
| Orders               | `POST /orders/{id}/accept`, `/reject`, navigation                       |
| POD                  | `/pod-photo`, `/pod-signature`, `/pod-complete`, OTP                    |
| Location             | `POST /location` (+ legacy `POST /driver/location`)                     |
| Shift / availability | `/shift/*`, `POST /availability`                                        |
| Offline              | `POST /offline/queue`, `GET /offline/pending`, `POST /offline/sync`     |
| Support              | `/support`, `/incidents`, `POST /emergency`                             |
| Push                 | `POST /push/register` → `DeviceService`                                 |

**Auth:** Porterchain JWT (`Authorization: Bearer`). Portal stores tokens in **httpOnly cookies** via BFF; mobile uses secure storage.

**Dev bypass:** `X-Driver-Id` / email-only paths when `CLERK_DEV_BYPASS=true` and `APP_ENV=local`.

---

## Fleetbase (adapter only)

| Capability       | Adapter path                             |
| ---------------- | ---------------------------------------- |
| GPS ping         | `DriverService.track_location`           |
| Online toggle    | `DriverService.toggle_online`            |
| POD upload       | `PodService.upload_proof`                |
| Route polyline   | Route/tracker APIs                       |
| Order state sync | `DriverFleetbaseBridge.sync_order_state` |

**Rule:** Never call Fleetbase from apps. Bridge gated by `fleetbase_dispatch_bridge`.

---

## Data model (PostgreSQL 16)

| Table                        | Purpose                        |
| ---------------------------- | ------------------------------ |
| `drivers`                    | Profile, wallet, compliance    |
| `orders.assigned_driver_id`  | Assignment                     |
| `driver_wallet_transactions` | Ledger                         |
| `driver_location_pings`      | GPS history                    |
| `driver_offline_actions`     | Offline queue                  |
| `driver_stop_meta`           | OTP, POD artifacts             |
| `notification_devices`       | FCM tokens (via push register) |

---

## Clients

```bash
pnpm dev:driver          # http://localhost:3003
pnpm dev:mobile-driver   # Expo
pnpm dev:api             # http://localhost:8001
```

**Web pages:** dashboard, jobs, navigation, shift, communications, earnings, profile, support, emergency.

**Mobile tabs:** Home, Jobs, Navigation, Earnings, Shift, More (profile, notifications, SOS, offline sync).

---

## Events (via `emit_event`)

- `order.driver_accepted` / `order.driver_rejected`
- `order.arrived_pickup`, pickup/delivery lifecycle
- `order.pod_completed`
- `driver.emergency`, `driver.shift_*`, `driver.route_changed`
- `notification.queued` (push/in-app)

---

## Related documents

- [CONNECTIONS.md](./CONNECTIONS.md) — mobile API contract
- [FLEETBASE_SERVICE_STATUS.md](./FLEETBASE_SERVICE_STATUS.md) — Fleetbase stack
- [EVENT_CATALOG.md](./EVENT_CATALOG.md)
- [DEVICE_REGISTRATION_FLOW.md](./docs/notifications/DEVICE_REGISTRATION_FLOW.md)

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
