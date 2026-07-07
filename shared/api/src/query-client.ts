import { QueryClient } from "@tanstack/react-query";
import type { ApiError } from "./errors";

export function createMobileQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 5 * 60_000,
        refetchOnMount: false,
        refetchOnReconnect: true,
        retry: (failureCount, error) => {
          const status = (error as ApiError)?.status;
          if (status === 401 || status === 403 || status === 404) return false;
          return failureCount < 2;
        },
      },
      mutations: {
        retry: false,
      },
    },
  });
}
