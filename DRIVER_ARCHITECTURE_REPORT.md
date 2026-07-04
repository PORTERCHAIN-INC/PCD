# Driver Platform — Architecture Report

**Reference:** [masterrule.md](./masterrule.md) v3.1  
**Date:** June 30, 2026

---

## 1. Locked topology

```
┌─────────────────────────────────────────────────────────────┐
│                    DRIVER CLIENTS                            │
│  apps/driver-portal (:3003)  │  apps/mobile-driver (Expo)   │
└────────────────────────────┬────────────────────────────────┘
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────┐
│              BFF (driver-portal only)                        │
│  /api/driver/* → :8001/driver-api/v1/*                      │
│  /api/auth/*   → login, session, ws-token                   │
└────────────────────────────┬────────────────────────────────┘
                             ▼
┌─────────────────────────────────────────────────────────────┐
│         PORTERCHAIN API — Logistics Orchestrator (:8001)     │
│  routers/driver.py          (Controller)                     │
│  driver_engine/             (Bridge, RBAC, offline executor)   │
│  porterchain_driver/*       (Application Services)           │
│  billing_engine/            (Finance — driver earnings)      │
│  notification_engine/       (FCM, in-app, WebSocket)         │
└──────────────┬──────────────────────────┬───────────────────┘
               │                          │
               ▼                          ▼
        PostgreSQL                  Internal Event Bus
               │                          │
               │                          ▼
               │              notification_engine/event_router
               │                          │
               ▼                          ▼
┌──────────────────────────┐    Driver push / in-app / WS
│  DriverFleetbaseBridge   │
│  fleetbase_bridge.py     │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  Fleetbase Adapter       │  services/fleetbase-adapter/
│  porterchain_fleetbase_  │
│  adapter/integration.py  │
└────────────┬─────────────┘
             ▼
┌──────────────────────────┐
│  Fleetbase Core (:8000)  │  Dispatch, GPS, Routes, POD
└──────────────────────────┘
```

### Inbound path (Fleetbase → Porterchain)

```
Fleetbase webhooks
  → routers/webhooks.py
  → fleetbase_engine/*
  → Order state updates + DomainEvent
  → event bus → notification_engine
  → Driver notifications (assignment, tracking, etc.)
```

Drivers **never** participate in the inbound webhook path. They only trigger outbound actions through the orchestrator.

---

## 2. Layer mapping (masterrule §3)

| Layer | Driver location | Responsibility |
|-------|-----------------|----------------|
| **UI** | `apps/driver-portal/src/` | Render, capture input, call BFF |
| **Controller** | `apps/api/.../routers/driver.py` | Auth, validate, delegate |
| **Application Service** | `services/driver-platform/porterchain_driver/` | All driver business logic |
| **Repository** | `driver_models.py`, `models.py` | Persistence |
| **Adapter** | `driver_engine/fleetbase_bridge.py` → `fleetbase-adapter/` | Fleetbase HTTP only here |

### Facade entry point

`DriverPlatform` (`platform.py`) exposes domain services:

| Service | Module | Domain |
|---------|--------|--------|
| `dashboard` | `dashboard.py` | KPIs, workspace snapshot |
| `jobs` | `jobs.py` | Job list, detail, history |
| `stops` | `stops.py` | Route, arrive, deliver, exception |
| `navigation` | `navigation.py` | Session, polyline, ETA |
| `shift` | `shift.py` | Shift lifecycle, availability |
| `availability` | `availability.py` | Accept/reject, online |
| `pod` | `pod.py` | OTP, photo, signature, complete |
| `location` | `location.py` | GPS pings |
| `earnings` / `finance` | `earnings.py`, `finance.py` | Finance Engine delegation |
| `profile` / `documents` / `vehicle` | `profile.py`, etc. | Compliance |
| `support_hub` | `support_bridge.py` | Admin Support/Claims bridge |
| `communications` | `communications.py` | Notification hub |
| `offline` | `offline.py` | Offline action queue |
| `push` | `push.py` | FCM device registration |

---

## 3. Communication rules verification

### Driver → Porterchain (outbound)

| Client action | Path | Service | Fleetbase |
|---------------|------|---------|-----------|
| Login | `POST /auth/login` | `DriverAuthService` | No |
| Dashboard | `GET /dashboard` | `DashboardService` | No |
| Accept job | `POST /orders/{id}/accept` | `AvailabilityService` | ✅ `DRIVER_ACCEPTED` |
| Reject job | `POST /orders/{id}/reject` | `AvailabilityService` | ✅ `DISPATCH_READY` |
| GPS ping | `POST /location` | `LocationService` | ✅ `track_driver_location` |
| Arrive/deliver | `POST .../arrive`, `/deliver` | `StopsService` | ✅ `sync_order_state` |
| POD capture | `POST .../pod-*` | `ProofOfDeliveryService` | ✅ upload + complete |
| Shift online | `POST /shift/*` | `ShiftService` | ✅ `toggle_driver_online` |
| Earnings | `GET /earnings` | `FinanceService` → billing_engine | No |
| Support/claims | `POST /support/*` | `SupportBridgeService` | No |
| Emergency | `POST /emergency` | `EmergencyService` | No (ops alert) |
| Offline sync | `POST /offline/sync` | `OfflineService` + executor | Per action |

### Porterchain → Driver (notifications)

| Event | Channel | Template |
|-------|---------|----------|
| `DRIVER_ASSIGNED` | push + in_app | `driver_assigned` |
| `DRIVER_ACCEPTED` | in_app | `driver_accepted` |
| `driver.route_changed` | push + in_app | `driver_route_changed` |
| `driver.emergency` | in_app admin | `driver_alert` |
| `CLAIM_OPENED` / `CLAIM_RESOLVED` | push + in_app | `claim_*` |
| `SUPPORT_TICKET_CREATED` | push + in_app | `support_ticket_created` |
| `incident.reported` | in_app | `driver_alert` |
| `driver.shift_*` | in_app | `driver_alert` |

---

## 4. Driver portal frontend architecture

```
src/app/
├── layout.tsx              CommunicationsProvider, GoogleMaps, Clerk
├── api/
│   ├── auth/               login, session, ws-token
│   └── driver/[...path]/   BFF proxy to driver-api
├── dashboard/              useDriverWorkspace
├── jobs/                   useDriverJobs, Delivery360
├── navigation/             useDriverNavigation, DriverNavigationMap
├── shift/                  useDriverShift
├── communications/         useDriverCommunications
├── earnings/               useDriverEarnings
├── profile/                useDriverProfile (documents, vehicle)
├── support/                useDriverSupport (claims, tickets, SOS)
└── emergency/              SOS (authenticated)

src/lib/
├── api.ts                  Central BFF client (~55 methods)
├── offline-client.ts       localStorage queue + GPS buffer
├── communications.ts       Types + group labels
└── [domain].ts             Typed DTOs per module
```

**No business logic in UI** — earnings displayed from API; finance never calculated client-side.

---

## 5. Offline architecture

```
┌──────────────┐     online      ┌─────────────────────┐
│ localStorage │ ──────────────► │ POST /offline/queue │
│ action queue │                 │ POST /offline/sync  │
│ GPS buffer   │                 └──────────┬──────────┘
└──────────────┘                            ▼
                                 DriverOfflineExecutor
                                 → porterchain_driver services
                                 → FleetbaseBridge (when applicable)
```

Supported offline actions: location, POD (photo/signature/barcode/complete), arrive/deliver, shift, availability, document_upload, incident, support_ticket.

---

## 6. Realtime architecture

| Stream | Mechanism | Scope |
|--------|-----------|-------|
| Notifications | WebSocket `/v1/notifications/ws` + 15s poll | Communications page |
| Jobs / shift / dashboard | HTTP polling (10–20s) | Module hooks |
| GPS | `watchPosition` + 25s POST | Navigation hook |
| Auto offline flush | 30s interval + `online` event | CommunicationsProvider |

---

## 7. RBAC model

```
DriverContext
  └── driver record (status: pending | approved | suspended)
        └── require_approved_driver() on execution mutations
```

- **Suspended:** blocked at auth layer (403)
- **Pending:** can view profile/documents; execution endpoints require approval
- **Approved:** full execution (shift, stops, POD, location, accept/reject)

No granular permission scopes — single driver role per masterrule driver boundary.

---

## 8. Architecture violations found

| Violation | Severity | Status |
|-----------|----------|--------|
| Direct WS to API host | Low (token scoped) | Documented; ws-token route |
| Synthetic route IDs | Medium | Known; Fleetbase route binding future |
| Earnings helper hardcoded cents | Low | Finance Engine is source of truth for statements |

**No Fleetbase HTTP from UI.** **No merchant/admin API bypass from driver clients.**

---

## 9. Related documents

- [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md)
- [DRIVER_INTEGRATION_MATRIX.md](./DRIVER_INTEGRATION_MATRIX.md)
- [DRIVER_SECURITY_REPORT.md](./DRIVER_SECURITY_REPORT.md)
- [DRIVER_PERFORMANCE_REPORT.md](./DRIVER_PERFORMANCE_REPORT.md)
- [DRIVER_AUDIT.md](./DRIVER_AUDIT.md)
- [masterrule.md](./masterrule.md)
