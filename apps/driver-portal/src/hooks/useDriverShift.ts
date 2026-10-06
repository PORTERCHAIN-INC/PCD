"use client";

import { useCallback, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";
import type { DriverShiftSnapshot } from "@/lib/shift";

const POLL_MS = 10_000;

export function useDriverShift() {
  const qc = useQueryClient();
  const [actionPending, setActionPending] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");
  const query = useQuery({
    queryKey: ["driver-shift"],
    queryFn: () => driverApi.shift(),
    refetchInterval: (current) => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return false;
      return current.state.data?.shift_active ? POLL_MS : false;
    },
  });
  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["driver-shift"] });
  }, [qc]);

  const runAction = useCallback(
    async (id: string, fn: () => Promise<DriverShiftSnapshot>) => {
      setActionPending(id);
      try {
        const snap = await fn();
        qc.setQueryData(["driver-shift"], snap);
        return snap;
      } catch (e) {
        setActionError(e instanceof Error ? e.message : `${id}_failed`);
        throw e instanceof Error ? e : new Error(`${id}_failed`);
      } finally {
        setActionPending(null);
      }
    },
    [qc]
  );

  const data = query.data ?? null;
  return {
    data,
    error:
      actionError ||
      (query.error instanceof Error
        ? query.error.message
        : query.error
          ? "shift_refresh_failed"
          : ""),
    loading: query.isLoading && !data,
    refreshing: query.isFetching && Boolean(data),
    actionPending,
    refresh,
    startShift: (routeId?: string, pretrip?: Record<string, boolean>) =>
      runAction("start", () => driverApi.shiftStart(routeId, pretrip)),
    endShift: () => runAction("end", () => driverApi.shiftEnd()),
    startBreak: () => runAction("break", () => driverApi.shiftBreak()),
    resumeShift: () => runAction("resume", () => driverApi.shiftResume()),
    setAvailability: (mode: "online" | "offline" | "busy" | "idle") =>
      runAction(mode, () => driverApi.setAvailabilityMode(mode)),
  };
}
