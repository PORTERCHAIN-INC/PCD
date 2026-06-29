"use client";

import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useEffect, useState } from "react";

export function useApiData<T>(loader: (token: string) => Promise<T>, deps: unknown[] = []) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    if (!isSignedIn && process.env.NODE_ENV !== "development") return;
    let cancelled = false;
    void (async () => {
      try {
        const token = await getApiToken();
        const result = await loader(token);
        if (!cancelled) setData(result);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, isSignedIn, getApiToken, ...deps]);

  return { data, error, isLoaded, isSignedIn, getApiToken };
}
