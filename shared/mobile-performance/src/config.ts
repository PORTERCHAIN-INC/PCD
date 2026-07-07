import type { PerformancePolicy } from "./types";

export const DEFAULT_PERFORMANCE_POLICY: PerformancePolicy = {
  listDrawDistance: 250,
  defaultEstimatedItemSize: 72,
  prefetchStaleTimeMs: 30_000,
  backgroundPollingPaused: true,
  websocketBackoffBaseMs: 4_000,
  websocketBackoffMaxMs: 60_000,
  imageCachePolicy: "memory-disk",
};
