# Driver Platform — Performance Report

**Last verified:** 2026-07-04  
**Reference:** [masterrule.md](./masterrule.md) §16 (Observability)  
**Scope:** `apps/driver-portal/`, `apps/mobile-driver/`, `/driver-api/v1/*`, `services/driver-platform/`

> **Platform status:** overall Porterchain is **not production ready** — see [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md). This report covers driver performance only.

---

## Executive Summary

| Area                     | Assessment        | Notes                                                                     |
| ------------------------ | ----------------- | ------------------------------------------------------------------------- |
| Web portal load          | Good for pilot    | Next.js portal with BFF proxy and route-level data hooks                  |
| Mobile runtime           | Good for beta     | Expo SDK 52, lazy screens, performance provider                           |
| Polling load             | Moderate          | Web uses interval polling; notifications use WS + polling fallback        |
| GPS upload volume        | Main scale driver | Mobile `expo-location`; web navigation/location flows post to `/location` |
| Offline sync             | Good              | Web local queue; mobile MMKV queue + driver server sync                   |
| Fleetbase bridge latency | Risk              | Execution actions can call Fleetbase adapter in request path              |
| Observability            | Partial           | Client diagnostics exist; backend driver metrics still sparse             |

**Verdict:** driver web and mobile are suitable for controlled pilot and internal/beta operations. Before scaling beyond ~100 active drivers, add driver-specific API metrics, bridge latency instrumentation, and job-status realtime updates.

---

## Current Surfaces

| Surface              | Performance Shape                                         | Status                  |
| -------------------- | --------------------------------------------------------- | ----------------------- |
| `apps/driver-portal` | Next.js BFF, polling hooks, httpOnly cookie session       | ✅ Pilot                |
| `apps/mobile-driver` | Expo SDK 52, native GPS, MMKV offline queue, lazy screens | ✅ Beta                 |
| `/driver-api/v1/*`   | ~75 route handlers; thin controller pattern               | ✅ Pilot                |
| Fleetbase adapter    | Track, status, POD upload, online/offline sync            | ⚠ Needs latency metrics |

---

## Web Portal Performance

| Module         | Pattern                             | Risk                                             |
| -------------- | ----------------------------------- | ------------------------------------------------ |
| Dashboard      | Multiple workspace reads            | Duplicate calls if dashboard and comms stay open |
| Jobs / detail  | Polling + mutations                 | No WS job-event subscription                     |
| Navigation     | Map rendering + location update     | Maps key and browser geolocation required        |
| Communications | WS token + HTTP fallback            | Reconnect/backoff should be hardened             |
| Offline        | localStorage queue + periodic flush | Sequential replay after long outage              |

### Web Recommendations

| Priority | Recommendation                                               |
| -------- | ------------------------------------------------------------ |
| P1       | Add job/route update events over WebSocket to reduce polling |
| P1       | Add reconnect with exponential backoff for notification WS   |
| P2       | Share dashboard/comms cache with TanStack Query or SWR       |
| P2       | Batch offline queue flushes when the backlog is large        |

---

## Mobile Driver Performance

| Capability         | Implementation                                                     | Status |
| ------------------ | ------------------------------------------------------------------ | ------ |
| Navigation         | `@porterchain/mobile-maps` + `EnterpriseMap`                       | ✅     |
| GPS                | `expo-location`, background task config, `/driver-api/v1/location` | ✅     |
| Offline            | `@porterchain/mobile-offline`, MMKV queue, 30s auto-sync           | ✅     |
| Lazy screens       | `@porterchain/mobile-performance` for heavy screens                | ✅     |
| Push/realtime      | `@porterchain/mobile-notifications`, FCM + WS                      | ✅     |
| Secure API refresh | `createSecureApiClient` with access/refresh token callbacks        | ✅     |

### Mobile Recommendations

| Priority | Recommendation                                                                 |
| -------- | ------------------------------------------------------------------------------ |
| P1       | Profile battery impact of background GPS during 8-hour shifts                  |
| P1       | Track offline sync success/failure rates as backend metrics                    |
| P2       | Add crash reporting (Sentry or equivalent) before store release                |
| P2       | Add Maestro/Detox performance smoke tests for sign-in, jobs, POD, and push tap |

---

## Backend Performance Risks

| Path                   | Risk                                   | Mitigation                                                 |
| ---------------------- | -------------------------------------- | ---------------------------------------------------------- |
| `POST /location`       | High request volume at fleet scale     | Time-series index, sampling policy, async bridge if needed |
| Accept/reject/stop/POD | Fleetbase call in execution path       | Adapter timeout <= 3s + circuit breaker                    |
| `/dashboard`, `/jobs`  | High fan-out under polling             | Aggregate endpoint and indexes on driver/order columns     |
| `/offline/sync`        | Backlog replay after connectivity loss | Batch processing and idempotency metrics                   |
| `/emergency`           | Burst/abuse risk                       | Dedicated rate limit and alerting                          |

---

## Load Model (Pilot)

Assumptions: 50 active drivers, 8-hour shifts, driver mobile active, some web portal sessions.

| Source                | Approximate Driver Rate             | Fleet Total                        |
| --------------------- | ----------------------------------- | ---------------------------------- |
| GPS pings             | 1 every 20-30s while online         | 6k-9k/hour                         |
| Web polling           | 3-6 requests/min/session            | 9k-18k/hour if all drivers use web |
| Mobile sync / actions | Bursty                              | Driven by execution events         |
| Notifications WS      | One connection per signed-in client | Low bandwidth                      |

GPS and Fleetbase bridge calls dominate scale planning. The API itself should be fine for pilot volumes on modest hardware when PostgreSQL indexes are in place.

---

## Observability Gaps

| Signal                         | Status                                |
| ------------------------------ | ------------------------------------- |
| Driver API request metrics     | ⚠ Partial / generic                   |
| Fleetbase bridge latency       | ❌ Not driver-specific                |
| Offline sync success rate      | ❌ Not exposed as ops metric          |
| GPS ingest rate                | ❌ Needs dashboard                    |
| Mobile crash reporting         | ❌ Not configured                     |
| Client performance diagnostics | ✅ Mobile performance package/screens |

Recommended counters/histograms:

- `driver_api_requests_total`
- `driver_location_pings_total`
- `driver_offline_sync_actions_total`
- `driver_fleetbase_bridge_latency_seconds`
- `driver_mobile_crashes_total`

---

## Performance Test Plan

| Test                    | Target                                            |
| ----------------------- | ------------------------------------------------- |
| 50 concurrent drivers   | No 5xx; p95 API < 2s                              |
| Location ping           | p95 < 300ms without Fleetbase slowness            |
| Navigation session      | p95 < 1.5s with adapter enabled                   |
| Offline sync 50 actions | < 30s end-to-end                                  |
| Job accept/reject       | p95 < 2s including Fleetbase bridge               |
| Mobile 8-hour shift     | Battery and memory within acceptable field limits |

---

## Related Documents

| Document                                                           | Purpose                           |
| ------------------------------------------------------------------ | --------------------------------- |
| [DRIVER_PRODUCTION_READINESS.md](./DRIVER_PRODUCTION_READINESS.md) | Driver rollout posture            |
| [DRIVER_INTEGRATION_MATRIX.md](./DRIVER_INTEGRATION_MATRIX.md)     | Integration coverage              |
| [MOBILE_PERFORMANCE_REPORT.md](./MOBILE_PERFORMANCE_REPORT.md)     | Mobile-specific performance notes |
| [PRODUCTION_READINESS_REPORT.md](./PRODUCTION_READINESS_REPORT.md) | Platform-wide blockers            |
