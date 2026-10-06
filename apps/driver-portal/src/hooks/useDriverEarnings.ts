"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { driverApi } from "@/lib/api";

export function useDriverEarnings() {
  const qc = useQueryClient();
  const snapQuery = useQuery({
    queryKey: ["driver-earnings"],
    queryFn: () => driverApi.earningsSnapshot(),
  });
  const statementQuery = useQuery({
    queryKey: ["driver-earnings-statements"],
    queryFn: async () => (await driverApi.earningsStatements()).statements,
  });
  const refresh = useCallback(async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["driver-earnings"] }),
      qc.invalidateQueries({ queryKey: ["driver-earnings-statements"] }),
    ]);
  }, [qc]);
  const error =
    snapQuery.error instanceof Error
      ? snapQuery.error.message
      : snapQuery.error
        ? "earnings_refresh_failed"
        : "";

  return {
    data: snapQuery.data ?? null,
    statements: statementQuery.data ?? [],
    error,
    loading: snapQuery.isLoading && !snapQuery.data,
    refreshing: snapQuery.isFetching && Boolean(snapQuery.data),
    refresh,
  };
}
