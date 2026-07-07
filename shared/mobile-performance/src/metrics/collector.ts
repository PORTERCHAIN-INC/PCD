let prefetchCount = 0;
let lastSyncLatencyMs: number | null = null;
let imageCacheClearedAt: string | null = null;
let websocketConnected = false;
let websocketPaused = false;

export function recordPrefetch() {
  prefetchCount += 1;
}

export function recordSyncLatency(ms: number) {
  lastSyncLatencyMs = ms;
}

export function setImageCacheClearedAt(iso: string) {
  imageCacheClearedAt = iso;
}

export function setWebsocketMetrics(connected: boolean, paused: boolean) {
  websocketConnected = connected;
  websocketPaused = paused;
}

export function getPerformanceSnapshot(queryCacheEntries: number, appState: string) {
  return {
    appState,
    websocketConnected,
    websocketPaused,
    queryCacheEntries,
    prefetchCount,
    imageCacheClearedAt,
    lastSyncLatencyMs,
    batteryOptimizationsActive: appState !== "active",
    lazyScreensLoaded: 0,
    updatedAt: new Date().toISOString(),
  };
}

export function resetPrefetchCount() {
  prefetchCount = 0;
}
