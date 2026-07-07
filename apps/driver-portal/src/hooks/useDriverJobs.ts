"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverJobsList } from "@/lib/jobs";
import { formatLastUpdated } from "@/lib/workspace";

const POLL_MS = 12_000;

export function useDriverJobs() {
  const [data, setData] = useState<DriverJobsList | null>(null);
  const [history, setHistory] = useState<DriverJobsList["completed"]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeMessage, setOptimizeMessage] = useState("");
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    try {
      const [jobs, hist] = await Promise.all([driverApi.jobs(), driverApi.jobsHistory()]);
      if (mounted.current) {
        setData(jobs);
        setHistory(hist.history);
        setLastUpdated(new Date());
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "refresh_failed");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, []);

  const optimize = useCallback(async () => {
    setOptimizing(true);
    setOptimizeMessage("");
    try {
      const result = await driverApi.optimizeJobs();
      if (mounted.current) {
        setData(result.jobs);
        setLastUpdated(new Date());
        setError("");
        const km = result.metrics.distance_km;
        const min = result.metrics.duration_minutes;
        setOptimizeMessage(
          km != null && min != null ? `Route optimized — ${km} km · ~${min} min` : "Route optimized"
        );
      }
    } catch (e) {
      if (mounted.current) {
        setError(e instanceof Error ? e.message : "optimize_failed");
      }
    } finally {
      if (mounted.current) setOptimizing(false);
    }
  }, []);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh(true);
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

  return {
    data,
    history,
    error,
    loading,
    optimizing,
    optimizeMessage,
    lastUpdated,
    lastUpdatedLabel: lastUpdated ? formatLastUpdated(lastUpdated) : null,
    refresh: () => refresh(true),
    optimize,
  };
}
