"use client";

import { useCallback, useEffect, useState } from "react";
import { fetchDriverOnboarding, type DriverOnboardingStatus } from "@/lib/onboarding";

export function useDriverOnboarding(pollMs = 30_000) {
  const [data, setData] = useState<DriverOnboardingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    setError("");
    try {
      const status = await fetchDriverOnboarding();
      setData(status);
      return status;
    } catch (err) {
      setError(err instanceof Error ? err.message : "onboarding_fetch_failed");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
    if (!pollMs) return;
    const id = window.setInterval(() => void refresh(), pollMs);
    return () => window.clearInterval(id);
  }, [pollMs, refresh]);

  return { data, loading, error, refresh };
}
