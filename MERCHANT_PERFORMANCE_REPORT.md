# Merchant Portal — Performance Report

**Date:** June 30, 2026

---

## Summary

Merchant portal performance is **adequate for production** at moderate scale. Primary patterns: parallel API fetches on dashboard, polling for live tracking, WebSocket-triggered refresh. Bottlenecks are **N+1-free aggregates** in reporting and **external Fleetbase latency** on tracking—not portal rendering.

| Area                    | Rating   | Status |
| ----------------------- | -------- | ------ |
| Dashboard load          | Good     | ✅     |
| Orders list             | Good     | ✅     |
| Live tracking           | Moderate | ⚠      |
| Reports export          | Good     | ✅     |
| WebSocket realtime      | Moderate | ⚠      |
| API gateway rate limits | Good     | ✅     |
| Database queries        | Good     | ✅     |

---

## Frontend performance

| Page         | Pattern                                       | Interval                 | Status |
| ------------ | --------------------------------------------- | ------------------------ | ------ |
| Dashboard    | Parallel KPI + activity + notifications fetch | WS refresh + 60s poll    | ✅     |
| Orders list  | Paginated `GET /orders`                       | WS refresh               | ✅     |
| Order 360    | Parallel detail + tracking                    | 10s tracking poll        | ⚠      |
| Track page   | Search + map                                  | 10s poll on active track | ⚠      |
| Billing      | Tab lazy load per section                     | On mount                 | ✅     |
| Reports      | Workspace + chart data                        | On demand                | ✅     |
| Integrations | Keys/webhooks/usage tabs                      | On demand                | ✅     |

**Maps:** `TrackingMap` loads Google Maps SDK once; marker updates on poll—not streaming GPS.

**Bundle:** Next.js app router; no heavy chart lib on all pages.

---

## Backend performance

| Endpoint                    | Query pattern                       | Status     |
| --------------------------- | ----------------------------------- | ---------- |
| `GET /dashboard`            | Aggregates (counts, sums)           | ✅         |
| `GET /orders`               | Indexed `merchant_id` + pagination  | ✅         |
| `GET /orders/{id}/360`      | Single order + joins                | ✅         |
| `GET /orders/{id}/tracking` | DB + Fleetbase HTTP + OSRM/Valhalla | ⚠ external |
| `GET /reports/workspace`    | reporting_engine SQL aggregates     | ✅         |
| `GET /reports/export`       | Streamed CSV generation             | ✅         |
| `GET /billing/overview`     | billing_engine aggregates           | ✅         |
| Integrations usage          | Paginated logs                      | ✅         |

**Fleetbase adapter:** Tracking latency dominated by upstream Fleetbase response time (typically 200–800ms). Cached where `integration_bridge` supports it.

---

## Realtime & polling strategy

```
useMerchantRealtime
  ├── WebSocket: /v1/notifications/ws
  │     └── on event → full page data refresh
  └── Fallback poll: 60_000 ms (dashboard, orders, track)
```

| Concern                        | Impact                              | Status                         |
| ------------------------------ | ----------------------------------- | ------------------------------ |
| Full refresh on WS message     | Extra API round-trips               | ⚠ acceptable at low event rate |
| 10s tracking poll on Order 360 | 6 req/min per open order            | ⚠ scale with concurrent users  |
| No SSE for GPS stream          | Map updates lag up to poll interval | ⚠                              |

**Recommendation (future, not blocking):** Targeted invalidation (refetch tracking only) instead of full `refresh()`.

---

## API gateway & rate limits

| Control            | Default                                   | Status |
| ------------------ | ----------------------------------------- | ------ |
| Per-key rate limit | Configurable via `gateway_engine`         | ✅     |
| Usage logging      | Async insert to `merchant_api_usage_logs` | ✅     |
| 429 responses      | Standard headers                          | ✅     |

Protects against runaway integrator traffic without affecting portal JWT users (separate path).

---

## Event bus & webhooks

| Stage                 | Performance note                  | Status |
| --------------------- | --------------------------------- | ------ |
| `emit_event`          | Async publish to Redis/stream     | ✅     |
| Worker delivery       | Concurrent workers; retry backoff | ✅     |
| Portal webhook log UI | Paginated                         | ✅     |

Webhook delivery does not block merchant HTTP response path.

---

## Caching

| Layer                     | Present                       | Status |
| ------------------------- | ----------------------------- | ------ |
| HTTP Cache-Control on API | Minimal                       | ⚠      |
| Redis for session/RBAC    | Via platform                  | ✅     |
| Fleetbase response cache  | Bridge-level where applicable | ⚠      |
| Next.js static assets     | CDN in deploy                 | ✅     |

---

## Scalability considerations

| Scenario                              | Expected behavior                               |
| ------------------------------------- | ----------------------------------------------- |
| 100 concurrent merchants on dashboard | Fine with current aggregates                    |
| 50 users on Order 360 with 10s poll   | ~300 tracking req/min — monitor Fleetbase       |
| Large report export (90d, 10k orders) | CSV stream; may take 5–15s                      |
| Bulk upload 500 rows                  | Single transaction batch; timeout risk at 1000+ |

---

## Performance checklist for production

- [ ] Enable connection pooling (PgBouncer) for API workers
- [ ] Set Fleetbase adapter timeout (avoid hung tracking requests)
- [ ] Monitor `merchant_api_usage_logs` p95 latency
- [ ] Alert on webhook delivery failure rate > 5%
- [ ] Load test: 50 parallel `GET /track/{n}` through merchant-api
- [ ] Verify OSRM/Valhalla endpoints are co-located or low-latency to API

---

## Classification by feature

| Feature           | Performance | Notes                                    |
| ----------------- | ----------- | ---------------------------------------- |
| Dashboard         | ✅          | Parallel fetches                         |
| Orders            | ✅          | Pagination                               |
| Book Delivery     | ✅          | Preview is heaviest (pricing + validate) |
| Tracking          | ⚠           | External deps                            |
| Live Map          | ⚠           | Poll-based                               |
| Billing           | ✅          | Tabbed lazy load                         |
| Reports           | ✅          | Engine aggregates                        |
| API/Webhooks      | ✅          | Gateway + async delivery                 |
| WebSocket         | ⚠           | Coarse refresh                           |
| Fleetbase Adapter | ⚠           | Upstream bound                           |
| OSRM / Valhalla   | ✅          | Fast when reachable                      |
