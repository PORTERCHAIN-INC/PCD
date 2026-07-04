# Driver Platform — Performance Report

**Reference:** [masterrule.md](./masterrule.md) §16 (Observability)  
**Date:** June 30, 2026

---

## Executive summary

| Area | Assessment | Impact |
|------|------------|--------|
| Initial page load | Good | Next.js static + dynamic hybrid |
| API polling load | Moderate | Multiple 10–20s intervals per session |
| GPS upload frequency | Low | 25s throttle per device |
| Offline queue | Good | Batched flush; 500 GPS cap |
| Build size | Good | `npm run build` ~7s; 23 routes |
| Realtime efficiency | Moderate | WS for notifications only |
| Database | Not profiled | Recommend load test on `/dashboard` + `/jobs` |

**Overall:** Suitable for **pilot fleet (<100 concurrent drivers)**. Scale polling and add connection pooling before 500+ concurrent.

---

## 1. Frontend performance

### Build metrics (driver-portal)

| Metric | Value |
|--------|-------|
| Next.js version | 16.2.9 (Turbopack) |
| Compile time | ~2.5s |
| TypeScript check | ~2.2s |
| Static routes | 23 |
| Build status | ✅ Passing |

### Bundle considerations

| Dependency | Purpose | Note |
|------------|---------|------|
| `@porterchain/maps` | Google Maps | Lazy via provider |
| `lucide-react` | Icons | Tree-shaken per import |
| Clerk | Auth | Conditional provider |

**No Firebase SDK** — reduces bundle; push is server-mediated.

### Page weight patterns

| Page | Data sources on load | Polling |
|------|---------------------|---------|
| Dashboard | 8 parallel API calls | 15s (`useDriverWorkspace`) |
| Jobs | 1–2 calls | 12s list / 10s detail |
| Navigation | Session + geolocation | 10s session poll |
| Shift | 1 call | 10s |
| Communications | Hub snapshot | 15s + WS |
| Earnings | 1 call | On mount only |
| Support | Hub snapshot | 20s |

**Worst case concurrent polls (dashboard + comms open):** ~4 requests/15s per driver from polling alone.

---

## 2. Polling inventory

| Hook | Interval | Endpoint(s) | Visible-only |
|------|----------|-------------|--------------|
| `useDriverWorkspace` | 15s | dashboard bundle | ✅ `visibilityState` |
| `useDriverJobs` | 12s | `/jobs` | ✅ |
| `useJobDetail` | 10s | `/jobs/{id}` | ✅ |
| `useDriverNavigation` | 10s | `/navigation/session` | ✅ |
| `useDriverShift` | 10s | `/shift` | ✅ |
| `useDriverCommunications` | 15s | `/communications` | ✅ |
| `useDriverSupport` | 20s | `/support/hub` | ✅ |
| `CommunicationsProvider` | 30s | offline flush | ✅ |

### Recommendations

| Issue | Recommendation | Priority |
|-------|----------------|----------|
| Duplicate dashboard + comms polls | Shared SWR/React Query cache | P2 |
| No poll backoff on error | Exponential backoff in hooks | P2 |
| Jobs don't use WS | Subscribe job events on WS | P1 |
| 8 parallel dashboard fetches | Single `/workspace` aggregate endpoint | P2 |

---

## 3. GPS and location performance

| Parameter | Value |
|-----------|-------|
| `watchPosition` | `enableHighAccuracy: true` |
| Upload throttle | 25 seconds |
| Offline buffer max | 500 pings |
| Flush strategy | Sequential POST on reconnect |

### Battery / network impact

- High accuracy GPS is battery-intensive — acceptable for active navigation.
- Throttle at 25s balances Fleetbase tracking vs bandwidth.
- Offline buffer prevents data loss; cap prevents unbounded localStorage growth.

**Recommendation:** Pause GPS watch when shift ended or tab hidden (currently continues in navigation hook).

---

## 4. Offline queue performance

| Parameter | Value |
|-----------|-------|
| Storage | localStorage |
| Queue key | `porterchain_driver_offline_queue` |
| GPS key | `porterchain_driver_gps_buffer` |
| Flush trigger | 30s interval, `online` event, manual sync |
| Server sync | `POST /offline/queue` per item then `POST /offline/sync` |

### Bottleneck

Sequential upload of queue items — large backlog after long offline period may take minutes.

**Recommendation:** Batch queue API (`POST /offline/queue/batch`) for P2.

---

## 5. WebSocket performance

| Parameter | Value |
|-----------|-------|
| Endpoint | `/v1/notifications/ws` |
| Ping interval | 25s |
| Fallback | 15s HTTP poll |
| Reconnect | ❌ No backoff (reconnect on mount only) |

**Impact:** Brief disconnects rely on polling — acceptable latency for notifications.

**Recommendation:** Add reconnect with exponential backoff (max 60s).

---

## 6. Backend API performance (architectural)

### Router pattern

- Thin controllers — minimal overhead
- `DriverFleetbaseBridge` instantiated per logistics request (not pooled)
- Fleetbase calls are synchronous in request path — **latency risk**

| Endpoint type | Fleetbase round-trip |
|---------------|---------------------|
| Dashboard read | None |
| Location ping | 1× track (async-capable) |
| Arrive/deliver | 1× status sync |
| POD upload | 1× media upload |
| Navigation session | 0–1× route fetch + maps |

**Recommendation:** When `fleetbase_dispatch_bridge=true`, set Fleetbase HTTP timeout ≤3s with circuit breaker (adapter layer).

### N+1 risks

| Service | Pattern |
|---------|---------|
| `jobs.list_jobs` | Query orders for driver — OK with index on `assigned_driver_id` |
| `communications.inbox` | Single query + group in memory |
| `offline.status` | Up to 200 actions per driver |

**Recommendation:** Index `driver_offline_actions(driver_id, status, created_at)`.

---

## 7. Caching opportunities

| Data | Cache strategy | TTL |
|------|----------------|-----|
| Knowledge base | CDN / stale-while-revalidate | 1h |
| Training modules | Static | 24h |
| Profile documents | Revalidate on upload | — |
| Navigation polyline | Per-route memory cache | 5 min |
| Dashboard KPIs | Not cached | Real-time |

---

## 8. Load estimates (pilot)

Assumptions: 50 active drivers, 8h shift, all pages open.

| Source | Requests/hour/driver | Fleet total/hour |
|--------|---------------------|------------------|
| Polling (avg 15s) | ~240 | 12,000 |
| GPS (25s) | ~1,152 | 57,600 |
| User actions | ~50 | 2,500 |
| **Total** | ~1,442 | ~72,100 |

PostgreSQL and API at `:8001` should handle this on modest hardware. Fleetbase track calls dominate external I/O.

---

## 9. Observability gaps

| Signal | Status |
|--------|--------|
| Structured logging | ⚠ Partial in services |
| Driver action metrics | ❌ No dedicated dashboard |
| Fleetbase bridge latency | ❌ Not instrumented |
| Offline sync success rate | ❌ Client-only |
| WebSocket connection count | ❌ Not exposed |

**Recommendation:** Add Prometheus counters for `driver_api_requests_total`, `fleetbase_bridge_latency_seconds`, `offline_sync_actions_total`.

---

## 10. Performance test plan

| Test | Target |
|------|--------|
| Dashboard load (p95) | < 800ms API aggregate |
| Navigation session (p95) | < 1.5s with Fleetbase |
| Location ping (p95) | < 300ms |
| Offline sync 50 items | < 30s |
| 50 concurrent drivers | No 5xx; p95 < 2s |
| Build CI | < 60s |

---

## 11. Verdict

Driver portal performance is **adequate for pilot deployment**. Primary scaling concerns are **GPS upload volume to Fleetbase** and **polling multiplication** across hooks. Consolidate polling, add WS for job updates, and instrument bridge latency before scaling past 100 concurrent drivers.
