export type PerformanceMetrics = {
  appState: "active" | "background" | "inactive" | "unknown";
  websocketConnected: boolean;
  websocketPaused: boolean;
  queryCacheEntries: number;
  prefetchCount: number;
  imageCacheClearedAt: string | null;
  lastSyncLatencyMs: number | null;
  batteryOptimizationsActive: boolean;
  lazyScreensLoaded: number;
  updatedAt: string;
};

export type PerformancePolicy = {
  listDrawDistance: number;
  defaultEstimatedItemSize: number;
  prefetchStaleTimeMs: number;
  backgroundPollingPaused: boolean;
  websocketBackoffBaseMs: number;
  websocketBackoffMaxMs: number;
  imageCachePolicy: "memory-disk" | "disk" | "memory";
};
