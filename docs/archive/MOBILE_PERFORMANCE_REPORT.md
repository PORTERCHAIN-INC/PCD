# Mobile Performance Report

**Last verified:** 2026-07-04  
**Package:** `@porterchain/mobile-performance` (`shared/mobile-performance/`)  
**Apps:** `apps/mobile-driver`, `apps/mobile-customer`

---

## Executive Summary

Both mobile apps use a shared performance layer with query focus management, lazy screens, FlashList, optimized images, foreground-aware intervals, and a runtime performance dashboard.

**Performance posture:** good for beta and internal field testing. Real-device battery, GPS, map, and offline replay tests are still required before store release.

---

## Optimization Matrix

| Area | Status | Implementation |
| ---- | ------ | -------------- |
| FlashList | ✅ | `EnterpriseFlashList`, `LIST_ITEM_SIZES` |
| Image optimization | ✅ | `OptimizedImage`, `clearImageCache`, `expo-image` |
| Lazy screens | ✅ | `createLazyScreen`, `asNavScreen` |
| Query focus | ✅ | `setupQueryFocusManager` via `PerformanceProvider` |
| Foreground-aware intervals | ✅ | `useForegroundAwareInterval`, `useForegroundAwarePolling` |
| Metrics | ✅ | `getPerformanceSnapshot`, performance dashboard |
| Prefetch tracking | ✅ | `usePrefetchOnFocus`, `recordPrefetch` |
| Offline sync latency | ✅ | `recordSyncLatency` |
| WS metrics | ✅ | `setWebsocketMetrics` |
| Cache clearing | ✅ | Query clear + image cache clear |

---

## Provider Wiring

Both apps wrap the tree with `PerformanceLayer`, which uses `PerformanceProvider`:

```
QueryClientProvider
└── PerformanceLayer
    └── PerformanceProvider
        ├── setupQueryFocusManager()
        ├── metrics refresh every 5s
        └── image cache clear when app backgrounds
```

The provider reports app state, query cache size, lazy screen count, WebSocket metrics, offline sync latency, and image-cache clearing.

---

## Lazy-Loaded Screens

| Screen | App | Trigger |
| ------ | --- | ------- |
| `PodScreen` | Driver | Jobs → POD |
| `IncidentScreen` | Driver | Jobs → incident |
| `NavigationScreen` | Driver | Navigation tab |
| `OfflineSyncScreen` | Both | More/Profile → Offline Sync |
| `SosScreen` | Driver | More → SOS |
| `PerformanceScreen` | Both | More/Profile → Performance |
| `LiveMapScreen` | Customer | Tracking → live map |
| `StripeCheckoutScreen` | Customer | Booking checkout |
| `ClaimsScreen` | Customer | Profile → Claims |

Lazy screen loads are counted by `getLazyScreenLoadCount()` and shown in the performance dashboard.

---

## List Performance

| Pattern | Status |
| ------- | ------ |
| High-traffic lists | Use `EnterpriseFlashList` with estimated item sizes |
| Static settings/profile menus | ScrollView/ListSection acceptable |
| Notification/history screens | FlashList-ready flattened list patterns |
| Driver jobs/queue | FlashList pattern used for large job data |
| Customer bookings/history/invoices/receipts | FlashList pattern used where list growth is expected |

Recommended defaults:

| Setting | Value |
| ------- | ----- |
| `estimatedItemSize` | 72px standard, larger presets for job queue/notifications |
| `drawDistance` | 250px |
| `removeClippedSubviews` | true |

---

## Image And Map Performance

| Concern | Current State | Recommendation |
| ------- | ------------- | -------------- |
| POD images | `OptimizedImage` available; driver POD uses image capture/preview flows | Keep previews compressed and upload via presigned URL |
| Customer receipts/invoices | Mostly data-driven screens | Use optimized image if receipt thumbnails are added |
| Maps | Driver navigation and customer tracking are isolated screens | Keep map screens lazy and unmount/freeze on blur |
| Image memory | Cleared when app backgrounds | Validate on older Android devices |

---

## Network And Battery

| Resource | Current Pattern | Risk |
| -------- | --------------- | ---- |
| Driver GPS | `expo-location`, background task config, `/driver-api/v1/location` | Battery during long shifts |
| Driver offline sync | 30s auto-sync foreground | Backlog replay after long outage |
| Customer offline sync | 45s auto-sync, local/stub server adapter | UX consistency |
| Notifications WS | Provider metrics and foreground handling | Token/auth review and reconnect behavior |
| React Query | 30s stale / 5m GC defaults | Optional persistence not enabled |

Recommendations:

- Tie high-accuracy/background GPS strictly to active shift/online state.
- Add backend metrics for offline sync latency and failures.
- Run 8-hour battery tests on representative Android and iOS devices.

---

## Performance Dashboard

| App | Path | Metrics |
| --- | ---- | ------- |
| Driver | More → Performance | app state, WS status, query cache count, prefetch count, offline sync latency, lazy screens, image cache timestamp |
| Customer | Profile → Performance | same shared dashboard metrics |

Actions: refresh metrics and clear query/image caches.

---

## Remaining Gaps

| Gap | Impact | Recommendation |
| --- | ------ | -------------- |
| No production crash/performance telemetry | Medium | Add Sentry or equivalent |
| GPS battery not field-tested | High for driver | 8-hour route test |
| No automated mobile E2E perf smoke | Medium | Maestro/Detox flows |
| Query cache not persisted | Low | Optional MMKV persistence for read-only data |
| Customer offline server sync incomplete | Medium | Add server reconciliation or document local-only |
| No frame/FPS monitoring | Low | Add Sentry performance or native frame metrics |

---

## Benchmark Targets

| Metric | Target |
| ------ | ------ |
| Cold start to signed-in home | < 3s on mid-range Android |
| Driver jobs list scroll | 60 FPS, no visible jank |
| Navigation map open | < 1.5s after data is cached |
| GPS battery drain | < 5% per foreground map hour, subject to device baseline |
| Offline sync 50 actions | < 10s on LTE |
| Push tap to target screen | < 2s after app foreground |

---

## Related Documents

| Document | Purpose |
| -------- | ------- |
| [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md) | Release readiness |
| [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md) | Architecture |
| [MOBILE_UI_REPORT.md](./MOBILE_UI_REPORT.md) | UI patterns |
| [DRIVER_PERFORMANCE_REPORT.md](./DRIVER_PERFORMANCE_REPORT.md) | Driver platform performance |
