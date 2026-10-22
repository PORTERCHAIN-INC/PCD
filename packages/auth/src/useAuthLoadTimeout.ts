"use client";

import { useEffect, useState } from "react";
import { reportAuthEvent } from "./authTelemetry";

export const CLERK_LOAD_TIMEOUT_MS = 15_000;

/**
 * True once Clerk has failed to load for `timeoutMs`. Pages show `AuthLoadFailed`
 * instead of an endless "Preparing sign-in…" spinner (blocked CDN, CSP, network).
 */
export function useAuthLoadTimeout(isLoaded: boolean, timeoutMs = CLERK_LOAD_TIMEOUT_MS): boolean {
  const [timedOut, setTimedOut] = useState(false);
  useEffect(() => {
    if (isLoaded) {
      setTimedOut(false);
      return;
    }
    const id = window.setTimeout(() => {
      setTimedOut(true);
      reportAuthEvent(
        typeof navigator !== "undefined" && navigator.onLine === false
          ? "offline"
          : "clerk_load_timeout"
      );
    }, timeoutMs);
    return () => window.clearTimeout(id);
  }, [isLoaded, timeoutMs]);
  return timedOut && !isLoaded;
}
