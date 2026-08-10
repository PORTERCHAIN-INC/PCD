"use client";

import { useCallback, useState } from "react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { api } from "@/lib/api";
import { fleetbaseSsoErrorMessage } from "@/lib/fleetbase-access";

export function useFleetbaseSso() {
  const { getApiToken } = useAdminAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const openConsole = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const token = await getApiToken();
      if (!token) throw new Error("missing_bearer_token");
      const session = await api.fleetbaseSso(token);
      if (!session.console_url) throw new Error("fleetbase_console_url_missing");
      if (!(await probeConsoleUp(session.console_url))) {
        throw new Error("fleetbase_console_unreachable");
      }
      window.open(session.console_url, "_blank", "noopener,noreferrer");
      return true;
    } catch (err) {
      setError(fleetbaseSsoErrorMessage(err));
      return false;
    } finally {
      setLoading(false);
    }
  }, [getApiToken]);

  const clearError = useCallback(() => setError(null), []);

  return { openConsole, loading, error, clearError };
}

/** Liveness probe for the console origin — no-cors fetch resolves iff a server answers. */
async function probeConsoleUp(consoleUrl: string): Promise<boolean> {
  try {
    const origin = new URL(consoleUrl).origin;
    await fetch(origin, {
      mode: "no-cors",
      cache: "no-store",
      signal: AbortSignal.timeout(4000),
    });
    return true;
  } catch {
    return false;
  }
}
