"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";

type UseApiDataOptions = {
  /** Stable cache key — required when deps is empty to avoid cross-page cache collisions. */
  key?: string;
  staleTime?: number;
  enabled?: boolean;
};

function shouldRetryQuery(error: unknown, failureCount: number) {
  if (failureCount >= 2) return false;
  const message = error instanceof Error ? error.message : String(error);
  return (
    message.includes("401") ||
    message.includes("403") ||
    message.includes("404") ||
    message.includes("porterchain_api_timeout") ||
    message.includes("Failed to fetch")
  );
}

export function useApiData<T>(
  loader: (token: string) => Promise<T>,
  deps: unknown[] = [],
  options: UseApiDataOptions = {}
) {
  const { getApiToken, isLoaded, isSignedIn, authReady } = useAdminAuth();
  const enabled =
    authReady &&
    isLoaded &&
    (isSignedIn || process.env.NODE_ENV === "development") &&
    (options.enabled ?? true);

  const cacheKey = options.key ?? (deps.length > 0 ? String(deps[0]) : undefined);
  if (!cacheKey && process.env.NODE_ENV === "development") {
    console.warn("useApiData: pass options.key or a deps entry to avoid cache collisions");
  }

  const query = useQuery({
    queryKey: ["admin", cacheKey ?? "anonymous", ...deps],
    enabled,
    staleTime: options.staleTime ?? 60_000,
    placeholderData: keepPreviousData,
    retry: shouldRetryQuery,
    retryDelay: (attempt) => 300 * (attempt + 1),
    queryFn: async () => {
      const token = await getApiToken();
      return loader(token);
    },
  });

  return {
    data: query.data ?? null,
    error: query.error instanceof Error ? query.error.message : query.error ? String(query.error) : null,
    loading: query.isLoading,
    isFetching: query.isFetching,
    isLoaded,
    isSignedIn,
    getApiToken,
    refetch: query.refetch,
  };
}
