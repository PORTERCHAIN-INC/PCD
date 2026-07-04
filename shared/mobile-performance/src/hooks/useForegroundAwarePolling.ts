import { useAppState } from "@porterchain/mobile-hooks";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";

export function useForegroundAwarePolling(intervalMs: number) {
  const appState = useAppState();
  const paused = DEFAULT_PERFORMANCE_POLICY.backgroundPollingPaused && appState !== "active";
  return paused ? false : intervalMs;
}
