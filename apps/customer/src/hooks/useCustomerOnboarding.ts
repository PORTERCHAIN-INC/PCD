"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchCustomerOnboarding, type PortalOnboardingStatus } from "@/lib/onboarding";

export function useCustomerOnboarding(pollMs = 30_000) {
  const [data, setData] = useState<PortalOnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async (token: string) => {
    setError("");
    try {
      const status = await fetchCustomerOnboarding(token);
      setData(status);
      return status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "onboarding_fetch_failed");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  return { data, loading, error, refresh, setLoading };
}
