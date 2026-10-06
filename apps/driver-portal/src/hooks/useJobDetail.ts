"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";
import { formatLastUpdated } from "@/lib/workspace";

const POLL_MS = 10_000;

export function useJobDetail(orderId: string) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ["driver-job", orderId],
    queryFn: () => driverApi.job(orderId),
    refetchInterval: () => {
      if (typeof document !== "undefined" && document.visibilityState === "hidden") return false;
      return POLL_MS;
    },
  });
  const refresh = useCallback(async () => {
    await qc.invalidateQueries({ queryKey: ["driver-job", orderId] });
  }, [orderId, qc]);
  const lastUpdated = query.dataUpdatedAt ? new Date(query.dataUpdatedAt) : null;

  return {
    job: query.data ?? null,
    error: query.error instanceof Error ? query.error.message : query.error ? "job_not_found" : "",
    loading: query.isLoading && !query.data,
    lastUpdated,
    lastUpdatedLabel: query.data && lastUpdated ? formatLastUpdated(lastUpdated) : null,
    refresh,
  };
}
