# Mobile Performance Report

**Audit date:** June 30, 2026  
**Package:** `@porterchain/mobile-performance` (`shared/mobile-performance/`)

---

## Executive summary

Mobile performance optimization is **implemented** via a shared performance package wired into both apps. List-heavy screens use **FlashList**, images use **expo-image**, polling/WebSocket/sync pause in background, and a **Performance Dashboard** exposes runtime metrics.

**Performance posture:** **Good** for current scale; monitor on real devices before launch.

---

## 1. Optimization matrix

| Area | Status | Implementation |
|------|--------|----------------|
| **FlashList** | ✅ | `EnterpriseFlashList` on jobs, bookings, history, invoices, receipts, notifications |
| **Image Optimization** | ✅ | `OptimizedImage` (`expo-image`) — cache, transition, recycling |
| **Lazy Loading** | ✅ | `createLazyScreen` — maps, POD, checkout, SOS, performance screens |
| **Bundle Splitting** | ✅ | Dynamic `import()` per lazy screen |
| **Memory Optimization** | ✅ | `removeClippedSubviews`, image cache clear on background, `freezeOnBlur` |
| **Background Tasks** | ✅ | Offline sync paused when backgrounded; driver GPS task registered |
| **Prefetch** | ✅ | `usePrefetchOnFocus` — e.g. jobs prefetches queue |
| **Caching** | ✅ | TanStack Query 30s stale / 5min GC; `setupQueryFocusManager` |
| **WebSocket Optimization** | ✅ | Exponential backoff; pause + disconnect in background; foreground-only ping |
| **Battery Optimization** | ✅ | `useForegroundAwarePolling` on LiveMap (15s) / Navigation (20s) |
| **Performance Dashboard** | ✅ | Profile / More → Performance screen |

---

## 2. List performance

### EnterpriseFlashList defaults

| Setting | Value |
|---------|-------|
| `estimatedItemSize` | 72px default (`LIST_ITEM_SIZES`) |
| `drawDistance` | 250px |
| `removeClippedSubviews` | true |

### Screens migrated from ScrollView

| Screen | App | Item size preset |
|--------|-----|------------------|
| NotificationCenter | Shared | `notification` (120) |
| JobsScreen | Driver | `standard` (72) |
| AssignmentQueueScreen | Driver | `jobQueue` (140) |
| BookingsScreen | Customer | `standard` |
| HistoryScreen | Customer | `standard` |
| InvoicesScreen | Customer | `standard` |
| ReceiptsScreen | Customer | `standard` |

---

## 3. Image performance

```typescript
<OptimizedImage
  source={{ uri: photoUri }}
  cachePolicy="memory-disk"
  transition={200}
  recyclingKey={uri}
/>
```

**Used in:** Driver `PodScreen` photo preview.

**Background:** `clearImageCache()` on app background to reduce memory pressure.

---

## 4. React Query caching

```typescript
// shared/api/src/query-client.ts
staleTime: 30_000
gcTime: 5 * 60_000
refetchOnMount: false
refetchOnReconnect: true
```

**Focus manager:** `AppState` → `focusManager.setFocused()` — pauses refetch-on-focus when backgrounded.

---

## 5. Network & battery

| Resource | Foreground | Background |
|----------|------------|------------|
| Live map polling | 15s | Paused |
| Navigation polling | 20s | Paused |
| WebSocket ping | 30s | Paused |
| WS connection | Connected | Disconnected |
| Offline auto-sync | 30s (driver) / 45s (customer) | Paused |
| Image memory cache | Active | Cleared |

**WebSocket reconnect:** Exponential backoff 4s → 60s max.

---

## 6. Lazy-loaded screens (bundle splitting)

| Screen | App | Load trigger |
|--------|-----|--------------|
| PodScreen | Driver | Navigate to POD |
| IncidentScreen | Driver | Navigate to incident |
| NavigationScreen | Driver | Navigation tab |
| OfflineSyncScreen | Both | More / Profile |
| SosScreen | Driver | More |
| PerformanceScreen | Both | More / Profile |
| LiveMapScreen | Customer | Tracking → map |
| StripeCheckoutScreen | Customer | Booking checkout |
| ClaimsScreen | Customer | Profile |

Metric: `getLazyScreenLoadCount()` tracked in Performance Dashboard.

---

## 7. Performance Dashboard

**Path:** More → Performance (driver) / Profile → Performance (customer)

**Metrics displayed:**
- App state (active/background)
- WebSocket connected / paused
- React Query cache entry count
- Prefetch operation count
- Last offline sync latency
- Lazy screens loaded count
- Image cache cleared timestamp

**Actions:** Refresh metrics, Clear caches (Query + image).

---

## 8. Provider wiring

```
QueryClientProvider
└── PerformanceProvider
    ├── setupQueryFocusManager()
    ├── Metrics poll (5s)
    └── Image cache clear on background
```

---

## 9. Remaining performance gaps

| Gap | Impact | Recommendation |
|-----|--------|----------------|
| Maps in scroll views | Medium | Keep map screens lazy; unmount on blur |
| Dual GPS paths (foreground watch + background task) | Battery | Tie background GPS to shift-online only |
| No query persistence | Low | Optional MMKV persist for offline reads |
| SupportScreen still ScrollView | Low | Migrate ticket list to FlashList |
| No FPS / frame drop monitoring | Low | Integrate Reanimated perf monitor or Sentry performance |
| Driver TS lint (React Navigation types) | Dev UX | Align `@types/react` versions |

---

## 10. Benchmark targets (pre-launch)

| Metric | Target |
|--------|--------|
| Cold start to signed-in home | < 3s on mid-range Android |
| Jobs list scroll | 60 FPS, no jank |
| Live map poll battery (1hr foreground) | < 5% drain |
| Offline sync 50 actions | < 10s on LTE |
| WS reconnect after background | < 5s |

---

## 11. Related documents

- [MOBILE_PRODUCTION_READINESS.md](./MOBILE_PRODUCTION_READINESS.md)
- [MOBILE_ARCHITECTURE_REPORT.md](./MOBILE_ARCHITECTURE_REPORT.md)
- [MOBILE_UI_REPORT.md](./MOBILE_UI_REPORT.md)
