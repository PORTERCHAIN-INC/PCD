# Porterchain — Realtime Communication Report

**Type:** REPORT
**masterrule:** [§21](./masterrule.md#21-simplification--essential-complexity)
**Last verified:** 2026-07-05

> **Snapshot report** — point-in-time audit. Current truth: [REALTIME_FLOW.md](docs/architecture/REALTIME_FLOW.md) (canonical doc).

**Reference:** [masterrule.md](./masterrule.md) §7 — all realtime via Porterchain API  
**Canonical topology:** [docs/architecture/REALTIME_FLOW.md](./docs/architecture/REALTIME_FLOW.md) (Group 26)

---

## Executive summary

| Channel                   | Status | Notes                           |
| ------------------------- | ------ | ------------------------------- |
| WebSocket (API)           | ✅     | Admin live map only             |
| HTTP polling              | ✅     | Ops, dashboards, merchant track |
| Event bus (async)         | ✅     | Redis streams / in-memory       |
| Server-Sent Events        | ❌     | Not used                        |
| Fleetbase realtime direct | ❌     | **Correct** — blocked           |

---

## WebSocket endpoints

| Endpoint                                     | Auth              | Payload                            | Interval | Consumer                         |
| -------------------------------------------- | ----------------- | ---------------------------------- | -------- | -------------------------------- |
| `WS /v1/admin/operations/live-map/ws?token=` | Clerk JWT (query) | `{"type":"snapshot","data":{...}}` | 5s push  | `apps/admin` `useLiveMapData.ts` |

**Implementation:** `routers/operations.py:live_map_ws` → `LiveMapService.snapshot()`

**Data sources (Porterchain PostgreSQL mirror only):**

- Active drivers + `DriverLocationPing`
- Vehicles, in-flight orders
- Route polylines from mirror
- Exception markers (partial)

No Fleetbase WebSocket from UI. ✅

---

## HTTP polling

| Surface                  | Interval            | Endpoint                                 | WS?          |
| ------------------------ | ------------------- | ---------------------------------------- | ------------ |
| Live map fallback        | 8s                  | `GET /v1/admin/operations/live-map`      | WS primary   |
| Operations control tower | ~15s                | `GET /v1/admin/operations/control-tower` | Poll         |
| Admin dashboard          | ~20s                | `GET /v1/admin/dashboard`                | Poll         |
| Merchant live track      | 10s                 | Merchant tracking API                    | Poll         |
| Customer track page      | On load             | `GET /v1/orders/{tracking}`              | Text-only UI |
| Driver navigation        | On demand + refresh | Driver API navigation session            | Poll         |

---

## Required surfaces audit

| Surface              | Status | Mechanism                                              |
| -------------------- | ------ | ------------------------------------------------------ |
| Live map (admin)     | ✅     | WS + 8s poll fallback                                  |
| Operations dashboard | ⚠️     | HTTP poll                                              |
| Order state changes  | ⚠️     | Event bus; UI manual refresh                           |
| Customer tracking    | ⚠️     | API data available; customer web map missing           |
| Driver live map      | ⚠️     | Driver portal + mobile `EnterpriseMap` when configured |
| Push notifications   | ⚠️     | FCM/email/SMS via worker — not inbox WS                |

---

## Event-driven chain

```
Fleetbase webhook (POST /webhooks/fleetbase)
  → WebhookProcessor
  → transition_order_state
  → order.* domain event
  → Merchant webhook fanout (queue)
  → LiveMapService reads DB on next WS tick (~5s)
```

**Typical ops map latency:** ≤5s after mirror update.

---

## Driver location path

```
Driver mobile/web
  → POST /driver-api/v1/location (or Fleetbase bridge)
  → Fleetbase execution GPS
  → Inbound webhook → order.tracking_updated
  → DriverLocationPing mirror
  → LiveMapService snapshot → admin WS
```

---

## Frontend clients

| App   | File                      | URL                                      |
| ----- | ------------------------- | ---------------------------------------- |
| Admin | `hooks/useLiveMapData.ts` | `wsLiveMapUrl(token)` from `lib/maps.ts` |

Reconnect: falls back to HTTP polling on WS failure.

---

## Security

| Check            | Status                |
| ---------------- | --------------------- |
| WS auth required | ✅ Clerk JWT in query |
| Public WS        | ❌ None               |
| CORS             | ✅ API-bound          |

---

## Worker / async (not push-to-UI)

Email, SMS, FCM push, billing, merchant webhooks — processed via Redis queues in `apps/worker/`. No portal notification inbox WebSocket.

---

## Gaps & recommendations

| ID  | Gap                                              | Priority |
| --- | ------------------------------------------------ | -------- |
| R1  | Order-specific WS for Order 360                  | P3       |
| R2  | Dashboard SSE or shared WS channel               | P2       |
| R3  | Customer web tracking map + 30s poll             | P2       |
| R4  | Merchant realtime already has 10s poll + map viz | —        |
| R5  | Notification inbox realtime                      | P3       |

**Constraint:** New realtime channels must terminate at Porterchain API — never Fleetbase streams from UI.

---

## Verification

```bash
# REST snapshot
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/v1/admin/operations/live-map

# WS (valid Clerk JWT)
wscat -c "ws://localhost:8001/v1/admin/operations/live-map/ws?token=YOUR_JWT"
```

---

## Related

| Document                                                                                             | Purpose                      |
| ---------------------------------------------------------------------------------------------------- | ---------------------------- |
| [NOTIFICATION_REPORT.md](./NOTIFICATION_REPORT.md)                                                   | Template coverage (E2E)      |
| [docs/notifications/NOTIFICATION_ARCHITECTURE.md](./docs/notifications/NOTIFICATION_ARCHITECTURE.md) | Push architecture (Group 29) |

---

## Governance

| Document                                   | Role              |
| ------------------------------------------ | ----------------- |
| [masterrule.md](masterrule.md)             | Architecture SSOT |
| [CTO_AUDIT_REPORT.md](CTO_AUDIT_REPORT.md) | Doc vs code audit |
