"use client";

import { useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchDriverOnboarding, type DriverOnboardingStatus } from "@/lib/onboarding";

const KEY = ["driver-onboarding"] as const;

export function useDriverOnboarding(pollMs = 30_000) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: KEY,
    queryFn: () => fetchDriverOnboarding(),
    refetchInterval: (q) => {
      if (!pollMs) return false;
      const data = q.state.data as DriverOnboardingStatus | undefined;
      if (data?.ready) return false;
      return pollMs;
    },
  });

  const refresh = useCallback(async () => {
    const result = await qc.fetchQuery({ queryKey: KEY, queryFn: () => fetchDriverOnboarding() });
    return result;
  }, [qc]);

  return {
    data: query.data ?? null,
    loading: query.isLoading || query.isFetching,
    error: query.error instanceof Error ? query.error.message : "",
    refresh,
  };
}
