"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { AppState, type AppStateStatus } from "react-native";
import { useQueryClient } from "@tanstack/react-query";
import { useAppState } from "@porterchain/mobile-hooks";
import { setupQueryFocusManager } from "../cache/query-focus";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";
import { clearImageCache } from "../image/OptimizedImage";
import { getLazyScreenLoadCount } from "../lazy/createLazyScreen";
import { getPerformanceSnapshot, setImageCacheClearedAt } from "../metrics/collector";
import type { PerformanceMetrics } from "../types";

type PerformanceContextValue = {
  metrics: PerformanceMetrics;
  refreshMetrics: () => void;
  clearCaches: () => Promise<void>;
};

const PerformanceContext = createContext<PerformanceContextValue | null>(null);

export type PerformanceProviderProps = {
  children: ReactNode;
};

export function PerformanceProvider({ children }: PerformanceProviderProps) {
  const queryClient = useQueryClient();
  const appState = useAppState();
  const [metrics, setMetrics] = useState<PerformanceMetrics>(() =>
    getPerformanceSnapshot(0, AppState.currentState) as PerformanceMetrics
  );

  const refreshMetrics = useCallback(() => {
    const cache = queryClient.getQueryCache();
    setMetrics({
      ...(getPerformanceSnapshot(cache.getAll().length, appState) as PerformanceMetrics),
      lazyScreensLoaded: getLazyScreenLoadCount(),
    });
  }, [appState, queryClient]);

  useEffect(() => {
    const teardown = setupQueryFocusManager();
    return teardown;
  }, []);

  useEffect(() => {
    refreshMetrics();
    const timer = setInterval(refreshMetrics, 5000);
    return () => clearInterval(timer);
  }, [refreshMetrics]);

  useEffect(() => {
    const onChange = (state: AppStateStatus) => {
      if (state === "active") return;
      if (!DEFAULT_PERFORMANCE_POLICY.backgroundPollingPaused) return;
      void clearImageCache().then(() => {
        setImageCacheClearedAt(new Date().toISOString());
        refreshMetrics();
      });
    };
    const sub = AppState.addEventListener("change", onChange);
    return () => sub.remove();
  }, [refreshMetrics]);

  const clearCaches = useCallback(async () => {
    queryClient.clear();
    await clearImageCache();
    setImageCacheClearedAt(new Date().toISOString());
    refreshMetrics();
  }, [queryClient, refreshMetrics]);

  const value = useMemo(
    () => ({ metrics, refreshMetrics, clearCaches }),
    [clearCaches, metrics, refreshMetrics]
  );

  return <PerformanceContext.Provider value={value}>{children}</PerformanceContext.Provider>;
}

export function usePerformance() {
  const ctx = useContext(PerformanceContext);
  if (!ctx) throw new Error("usePerformance must be used within PerformanceProvider");
  return ctx;
}
