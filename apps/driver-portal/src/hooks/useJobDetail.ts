"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { driverApi } from "@/lib/api";
import type { DriverJobDetail } from "@/lib/jobs";
import { formatLastUpdated } from "@/lib/workspace";

const POLL_MS = 10_000;

export function useJobDetail(orderId: string) {
  const [job, setJob] = useState<DriverJobDetail | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const mounted = useRef(true);

  const refresh = useCallback(async () => {
    try {
      const detail = await driverApi.job(orderId);
      if (mounted.current) {
        setJob(detail);
        setLastUpdated(new Date());
        setError("");
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : "job_not_found");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [orderId]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") refresh();
    }, POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(interval);
    };
  }, [refresh]);

  return {
    job,
    error,
    loading,
    lastUpdated,
    lastUpdatedLabel: lastUpdated ? formatLastUpdated(lastUpdated) : null,
    refresh,
  };
}
