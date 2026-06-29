# Porterchain Driver Platform

**Document version:** 1.0  
**Date:** June 29, 2026  
**Package:** `services/driver-platform` (`porterchain-driver`)

---

## Purpose

The Porterchain Driver Platform **extends Fleetbase** — it does not replace it. Fleetbase remains the logistics execution engine (dispatch, GPS, routing). Porterchain owns the driver experience: earnings, wallet, compliance, POD capture, training, and support.

```
Driver App / Portal
        │
        ▼
/driver-api/v1/*  (Porterchain API)
        │
        ├── porterchain_driver (reusable services)
        │
        └── Fleetbase Adapter (sync only)
                │
                ▼
            Fleetbase API
```

---

## Architecture

| Layer               | Path                                           | Role                                            |
| ------------------- | ---------------------------------------------- | ----------------------------------------------- |
| Reusable services   | `services/driver-platform/porterchain_driver/` | Business logic — dashboard, earnings, POD, etc. |
| API engine          | `apps/api/.../driver_engine/`                  | Auth, Fleetbase bridge, RBAC                    |
| API routes          | `apps/api/.../routers/driver.py`               | `/driver-api/v1/*` REST                         |
| Web portal          | `apps/driver-portal/`                          | Next.js dashboard (port 3003)                   |
| Mobile (planned)    | `apps/mobile-driver/`                          | Expo app — same API                             |
| Fleetbase extension | `services/fleetbase-adapter/`                  | `track`, `toggle-online`, POD upload            |

---

## Reusable services (`DriverPlatform`)

| Service      | Module            | Capabilities                                  |
| ------------ | ----------------- | --------------------------------------------- |
| Dashboard    | `dashboard.py`    | Today's earnings, stops, wallet, performance  |
| Earnings     | `earnings.py`     | Today/week totals, per-route, delivery credit |
| Wallet       | `wallet.py`       | Balance, transactions, payouts                |
| Stops        | `stops.py`        | Assigned route, arrive, deliver, exceptions   |
| Bonuses      | `bonuses.py`      | List, claim                                   |
| Performance  | `performance.py`  | Score, on-time %, completion                  |
| Availability | `availability.py` | Online/offline, accept/reject assignment      |
| Vehicle      | `vehicle.py`      | Active vehicle, list, update                  |
| Insurance    | `insurance.py`    | Compliance status                             |
| Documents    | `documents.py`    | Upload, list, pending count                   |
| Ratings      | `ratings.py`      | Rating summary, feedback                      |
| Support      | `support.py`      | Tickets                                       |
| Training     | `training.py`     | Modules, completion                           |
| Incidents    | `incidents.py`    | Report, list                                  |
| Emergency    | `emergency.py`    | Distress alert → ops ticket + event           |
| Offline      | `offline.py`      | Queue actions for sync                        |
| Push         | `push.py`         | Device registration, notification events      |
| Navigation   | `navigation.py`   | Route polyline, maps URL via Fleetbase        |
| POD          | `pod.py`          | OTP, photo, barcode, signature, complete      |
| Location     | `location.py`     | GPS pings → Porterchain + Fleetbase           |

Usage:

```python
from porterchain_driver import DriverPlatform

platform = DriverPlatform()
snap = platform.dashboard.snapshot(db, driver)
```

---

## API (`/driver-api/v1`)

| Area           | Endpoints                                                                                |
| -------------- | ---------------------------------------------------------------------------------------- |
| Auth           | `POST /auth/login`                                                                       |
| Profile        | `GET /me`, `GET /dashboard`                                                              |
| Earnings       | `GET /earnings/today`, `GET /routes/{id}/earnings`                                       |
| Wallet         | `GET /wallet`                                                                            |
| Bonuses        | `GET /bonuses`, `POST /bonuses/{id}/claim`                                               |
| Performance    | `GET /performance`, `GET /ratings`                                                       |
| Availability   | `POST /availability`                                                                     |
| Routes & stops | `GET /routes/assigned`, `POST /routes/{id}/start`, `GET /routes/{id}/stops`              |
| Execution      | `POST /routes/{id}/stops/{stopId}/arrive`, `/deliver`, `/exception`                      |
| Orders         | `POST /orders/{id}/accept`, `/reject`, `GET /orders/{id}/navigation`                     |
| POD            | `/pod-photo`, `/pod-signature`, `/pod-barcode`, `/pod-complete`, `POST /orders/{id}/otp` |
| Location       | `POST /location`, legacy `POST /driver/location`                                         |
| Compliance     | `GET /vehicle`, `/insurance`, `/documents`, `POST /documents`                            |
| Support        | `GET/POST /support`, `GET/POST /incidents`, `POST /emergency`                            |
| Training       | `GET /training`, `POST /training/{id}/complete`                                          |
| Push           | `POST /push/register`                                                                    |
| Offline        | `POST /offline/queue`, `GET /offline/pending`                                            |

Auth: Porterchain JWT (`Authorization: Bearer`). Dev bypass: `X-Driver-Id` header when `CLERK_DEV_BYPASS=true`.

---

## Fleetbase extensions (adapter only)

| Capability     | Fleetbase API                         | Adapter method                            |
| -------------- | ------------------------------------- | ----------------------------------------- |
| GPS ping       | `POST /v1/drivers/{id}/track`         | `DriverService.track_location`            |
| Online toggle  | `POST /v1/drivers/{id}/toggle-online` | `DriverService.toggle_online`             |
| POD upload     | `POST /v1/orders/{id}/proofs`         | `PodService.upload_proof`                 |
| Route polyline | `GET /v1/orders/{id}/tracker`         | `RouteService.extract_route_from_tracker` |

**Rule:** Never call Fleetbase from apps directly. All sync goes through `DriverFleetbaseBridge` → `FleetbaseAdapter`.

---

## Data model

| Table                        | Purpose                                   |
| ---------------------------- | ----------------------------------------- |
| `drivers`                    | Profile, wallet balance, compliance flags |
| `orders.assigned_driver_id`  | Driver assignment                         |
| `driver_wallet_transactions` | Wallet ledger                             |
| `driver_bonuses`             | Bonus programs                            |
| `driver_location_pings`      | GPS history                               |
| `driver_incidents`           | Incident reports                          |
| `driver_offline_actions`     | Offline sync queue                        |
| `driver_stop_meta`           | OTP hashes, POD artifacts                 |

---

## Driver portal

```bash
pnpm dev:driver   # http://localhost:3003
pnpm dev:api      # http://localhost:8001
```

Login with approved driver email → JWT stored in `localStorage`.

Pages: Dashboard, Today's Stops, Earnings, Wallet, Performance, Vehicle, Insurance, Documents, Training, Support, Emergency.

---

## Events

Driver actions emit domain events via `emit_event()`:

- `driver.online` / `driver.offline`
- `order.driver_accepted` / `order.driver_rejected`
- `order.arrived_pickup`, `order.pickup_completed`, `order.delivered`
- `order.pod_completed` (ProofCompleted)
- `driver.emergency`
- `notification.queued` (push)

---

## Related documents

- [CONNECTIONS.md](./CONNECTIONS.md) — mobile API contract
- [FLEETBASE_ADAPTER_ARCHITECTURE.md](./FLEETBASE_ADAPTER_ARCHITECTURE.md) — adapter boundary
- [EVENT_CATALOG.md](./EVENT_CATALOG.md) — domain events
- [DOMAIN_MODEL.md](./DOMAIN_MODEL.md) — Driver aggregate
