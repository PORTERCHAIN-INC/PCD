"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverShiftSnapshot } from "@/lib/shift";

const POLL_MS = 10_000;

export function useDriverShift() {
  const [data, setData] = useState<DriverShiftSnapshot | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [actionPending, setActionPending] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setRefreshing(true);
    try {
      const snap = await driverApi.shift();
      if (mounted.current) {
        setData(snap);
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "shift_refresh_failed");
    } finally {
      if (mounted.current) {
        setLoading(false);
        setRefreshing(false);
      }
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

  const runAction = useCallback(
    async (id: string, fn: () => Promise<DriverShiftSnapshot>) => {
      setActionPending(id);
      try {
        const snap = await fn();
        if (mounted.current) {
          setData(snap);
          setError("");
        }
      } catch (e) {
        if (mounted.current) setError(e instanceof Error ? e.message : `${id}_failed`);
        throw e;
      } finally {
        if (mounted.current) setActionPending(null);
      }
    },
    []
  );

  return {
    data,
    error,
    loading,
    refreshing,
    actionPending,
    refresh: () => refresh(true),
    startShift: (routeId?: string) =>
      runAction("start", () => driverApi.shiftStart(routeId)),
    endShift: () => runAction("end", () => driverApi.shiftEnd()),
    startBreak: () => runAction("break", () => driverApi.shiftBreak()),
    resumeShift: () => runAction("resume", () => driverApi.shiftResume()),
    setAvailability: (mode: "online" | "offline" | "busy" | "idle") =>
      runAction(mode, () => driverApi.setAvailabilityMode(mode)),
  };
}
