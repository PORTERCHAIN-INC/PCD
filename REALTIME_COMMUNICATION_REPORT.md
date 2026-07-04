# Porterchain — Realtime Communication Report

**Reference:** [masterrule.md](./masterrule.md) §7 — all realtime via Porterchain API  
**Audit date:** June 30, 2026

---

## Executive summary

| Channel                   | Implemented                                | Gap                            |
| ------------------------- | ------------------------------------------ | ------------------------------ |
| WebSocket (API)           | ✅ Live map only                           | Orders, drivers, ops dashboard |
| HTTP polling              | ✅ Admin dashboard, ops, live-map fallback | —                              |
| Event bus (async)         | ✅ Redis Streams / in-memory               | —                              |
| Server-Sent Events        | ❌                                         | Not used                       |
| Fleetbase realtime direct | ❌ Correct — blocked                       | —                              |

---

## WebSocket endpoints

| Endpoint                                     | Auth                  | Payload                            | Interval | Consumer                         |
| -------------------------------------------- | --------------------- | ---------------------------------- | -------- | -------------------------------- |
| `WS /v1/admin/operations/live-map/ws?token=` | Clerk JWT query param | `{"type":"snapshot","data":{...}}` | 5s push  | `apps/admin` `useLiveMapData.ts` |

**Implementation:** `routers/operations.py:live_map_ws` → `LiveMapService.snapshot()`

**Data sources (all Porterchain DB mirror):**

- Active drivers + last `DriverLocationPing`
- Vehicles
- In-flight orders (state filter)
- Route polylines from mirror
- Incident/exception markers (partial)

**No Fleetbase WebSocket or HTTP polling from WS handler.** ✅

---

## HTTP polling (realtime fallback)

| Surface                  | Interval    | Endpoint                                 | WebSocket?   |
| ------------------------ | ----------- | ---------------------------------------- | ------------ |
| Live map                 | 8s fallback | `GET /v1/admin/operations/live-map`      | WS primary   |
| Operations control tower | 15s         | `GET /v1/admin/operations/control-tower` | ❌ Poll only |
| Admin dashboard          | 20s         | `GET /v1/admin/dashboard`                | ❌ Poll only |
| Website tracking         | On load     | `GET /v1/orders/{tracking}`              | ❌ No poll   |
| Merchant track           | On load     | `GET /v1/merchant/track`                 | ❌           |
| Driver stops             | On load     | `GET /driver-api/v1/routes/assigned`     | ❌           |

---

## Required realtime surfaces (Step 16 audit)

| Surface              | Status     | Mechanism                                               |
| -------------------- | ---------- | ------------------------------------------------------- |
| Orders               | ⚠️ Partial | State changes via event bus; UI polls or manual refresh |
| Tracking             | ⚠️ Partial | `order.tracking_updated` events; no WS to customer      |
| Live Map             | ✅         | WebSocket + poll fallback                               |
| Drivers              | ⚠️ Partial | Location pings → DB → live map WS                       |
| Notifications        | ❌         | No push WS to portals; email/SMS via worker             |
| Operations Dashboard | ⚠️ Partial | 15–20s HTTP poll                                        |

---

## Event-driven realtime chain

```
Fleetbase webhook
  → webhook.received
  → WebhookProcessor
  → transition_order_state
  → order.* domain event
  → [merchant webhook fanout queue — stub]
  → LiveMapService reads DB on next WS tick (5s)
```

**Latency:** Up to 5s for live map reflection of Fleetbase GPS updates (acceptable for ops mirror pattern).

---

## Driver location realtime

```
Driver mobile/web
  → POST /driver-api/v1/location
  → DriverFleetbaseBridge.track_driver_location
  → Fleetbase API
  → (webhook) order.location / driver.location
  → WebhookProcessor → order.tracking_updated
  → DriverLocationPing mirror (if implemented in processor)
  → LiveMapService snapshot
```

---

## Frontend WebSocket clients

| App   | File                      | URL construction                                                 |
| ----- | ------------------------- | ---------------------------------------------------------------- |
| Admin | `hooks/useLiveMapData.ts` | `ws(s)://{API}/v1/admin/operations/live-map/ws?token={clerkJwt}` |
| Admin | `lib/maps.ts`             | `wsLiveMapUrl()` helper                                          |

**Reconnect:** Hook falls back to HTTP polling on WS failure.

---

## Security

| Check               | Status                |
| ------------------- | --------------------- |
| WS auth required    | ✅ Clerk JWT in query |
| Public WS endpoints | ❌ None               |
| Driver WS           | ❌ Not implemented    |
| CORS for WS         | ✅ Same-origin API    |

---

## Worker / queue realtime

| Queue               | Realtime to UI?        |
| ------------------- | ---------------------- |
| EMAILS / SMS / PUSH | ❌ Async delivery only |
| BILLING             | ❌ Backend only        |
| WEBHOOKS            | ❌ Stub processor      |

Notifications are **push-out** (email/SMS), not **push-to-UI**.

---

## Gaps & recommendations

| ID  | Gap                         | Priority | Approach                                 |
| --- | --------------------------- | -------- | ---------------------------------------- |
| R1  | No order-specific WS        | P3       | Extend ops WS or SSE for order 360       |
| R2  | Dashboard poll-only         | P2       | Reuse live-map WS pattern or 10s SSE     |
| R3  | Customer tracking not live  | P2       | Poll `/tracking` every 30s on track page |
| R4  | Driver portal no live map   | P2       | Viz-only Google map + API route polyline |
| R5  | Notification inbox realtime | P3       | Future — FCM/web push                    |
| R6  | Merchant order status push  | P3       | Merchant webhook fanout (worker stub)    |

**Architecture constraint:** All new realtime channels must terminate at Porterchain API — never subscribe to Fleetbase streams from UI.

---

## Verification

```bash
# Live map WS (requires valid Clerk token)
wscat -c "ws://localhost:8001/v1/admin/operations/live-map/ws?token=YOUR_JWT"

# Snapshot REST
curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/v1/admin/operations/live-map
```
