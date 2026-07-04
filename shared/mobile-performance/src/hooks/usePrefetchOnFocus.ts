import { useCallback } from "react";
import { useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useFocusEffect } from "@react-navigation/native";
import { DEFAULT_PERFORMANCE_POLICY } from "../config";
import { recordPrefetch } from "../metrics/collector";

export function usePrefetchOnFocus<T>(
  queryKey: QueryKey,
  queryFn: () => Promise<T>,
  staleTime = DEFAULT_PERFORMANCE_POLICY.prefetchStaleTimeMs
) {
  const queryClient = useQueryClient();

  useFocusEffect(
    useCallback(() => {
      void queryClient.prefetchQuery({
        queryKey,
        queryFn,
        staleTime,
      });
      recordPrefetch();
    }, [queryClient, queryFn, queryKey, staleTime])
  );
}
