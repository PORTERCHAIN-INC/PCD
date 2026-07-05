# Merchant Portal — Performance Report

**Last verified:** 2026-07-04  
**See also:** [MERCHANT_ARCHITECTURE_REPORT.md](./MERCHANT_ARCHITECTURE_REPORT.md) · [PERFORMANCE_AUDIT.md](./PERFORMANCE_AUDIT.md)

---

## Summary

Merchant portal performance is **adequate for moderate scale**. Patterns: parallel dashboard fetches, WebSocket-triggered refresh with 60s poll fallback, 10s tracking polls on Order 360/track. Bottlenecks are **Fleetbase latency** on live tracking and **coarse WS refresh** — not Next.js rendering.

| Area | Rating | Status |
| ---- | ------ | ------ |
| Dashboard load | Good | ✅ |
| Orders list | Good | ✅ |
| Live tracking | Moderate | ⚠ |
| Reports export | Good | ✅ |
| WebSocket realtime | Moderate | ⚠ |
| API gateway rate limits | Good | ✅ |
| Database queries | Good | ✅ |

---

## Frontend performance

| Page | Pattern | Interval | Status |
| ---- | ------- | -------- | ------ |
| Dashboard | Parallel KPI + activity + notifications | WS + 60s poll | ✅ |
| Orders list | Paginated `GET /orders` | WS refresh | ✅ |
| Order 360 | Detail + tracking | 10s tracking poll | ⚠ |
| Track page | Search + map | 10s poll when active | ⚠ |
| Billing | Tab lazy load | On mount | ✅ |
| Reports | Workspace on demand | On demand | ✅ |
| Integrations | Tabbed keys/webhooks/usage | On demand | ✅ |

**Maps:** `@porterchain/maps` — SDK loaded once; markers update on poll (not streaming GPS).

---

## Backend performance

| Endpoint | Pattern | Status |
| -------- | ------- | ------ |
| `GET /dashboard` | Aggregates | ✅ |
| `GET /orders` | Indexed `merchant_id` + pagination | ✅ |
| `GET /orders/{id}/360` | Single order + joins | ✅ |
| `GET /orders/{id}/tracking` | DB + Fleetbase + MapsService | ⚠ external |
| `GET /reports/*` | SQL aggregates | ✅ |
| `GET /billing/*` | billing_engine aggregates | ✅ |
| Integrations usage | Paginated `merchant_api_usage_logs` | ✅ |

PostgreSQL 16 with performance indexes (migration `m1n2o3p4q5r6`).

---

## Realtime strategy

```
useMerchantRealtime (hooks/useMerchantRealtime.ts)
  ├── WebSocket: /v1/notifications/ws?token=&org_id=
  │     └── type=notification → onRefresh()
  ├── Ping every 30s
  └── Fallback poll: 60_000 ms
```

| Concern | Impact | Status |
| ------- | ------ | ------ |
| Full refresh on WS message | Extra API round-trips | ⚠ acceptable at low volume |
| 10s tracking poll | ~6 req/min per open order view | ⚠ monitor Fleetbase |
| No merchant GPS WebSocket | Map lags up to poll interval | ⚠ (platform policy) |

**Future:** Targeted refetch (tracking only) instead of full page refresh.

---

## API gateway

| Control | Status |
| ------- | ------ |
| Per-key rate limit (`gateway_engine`) | ✅ |
| Async usage logging | ✅ |
| 429 + `Retry-After` | ✅ |

Portal JWT traffic uses separate `PortalRateLimitMiddleware` (not gateway).

---

## Production checklist

- [ ] Connection pooling for API workers
- [ ] Fleetbase adapter HTTP timeout configured
- [ ] Monitor `merchant_api_usage_logs` p95
- [ ] Alert webhook delivery failure rate > 5%
- [ ] OSRM/Valhalla co-located or low-latency to API (`:8002`)
- [ ] Load test parallel `GET /track/{n}` via merchant-api

---

## Feature classification

| Feature | Performance | Notes |
| ------- | ----------- | ----- |
| Dashboard / Orders / Book | ✅ | Parallel or single-shot |
| Tracking / Live map | ⚠ | Poll + Fleetbase bound |
| Billing / Reports / API | ✅ | Aggregates + async webhooks |
| Valhalla / OSRM | ✅ | Fast when reachable |
