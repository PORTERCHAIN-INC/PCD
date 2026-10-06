"use client";

import { useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCustomerOnboarding, type PortalOnboardingStatus } from "@/lib/onboarding";

const KEY = ["customer-onboarding"] as const;

export function useCustomerOnboarding(pollMs = 30_000) {
  const qc = useQueryClient();
  const { getToken, isLoaded, isSignedIn } = useAuth();
  const enabled = Boolean(isLoaded && isSignedIn);

  const query = useQuery({
    queryKey: KEY,
    enabled,
    queryFn: async () => {
      const token = await getToken();
      if (!token) throw new Error("Not authenticated");
      return fetchCustomerOnboarding(token);
    },
    refetchInterval: (q) => {
      if (!pollMs || !enabled) return false;
      const data = q.state.data as PortalOnboardingStatus | undefined;
      if (data?.ready) return false;
      return pollMs;
    },
  });

  const refresh = useCallback(
    async (token?: string | null) => {
      const result = await qc.fetchQuery({
        queryKey: KEY,
        queryFn: async () => {
          const t = token ?? (await getToken());
          if (!t) throw new Error("Not authenticated");
          return fetchCustomerOnboarding(t);
        },
      });
      return result;
    },
    [getToken, qc]
  );

  return {
    data: query.data ?? null,
    loading: query.isLoading || query.isFetching,
    error: query.error instanceof Error ? query.error.message : "",
    refresh,
  };
}
