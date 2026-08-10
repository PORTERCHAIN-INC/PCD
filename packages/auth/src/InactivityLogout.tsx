"use client";

import { useAuth, useClerk } from "@clerk/nextjs";
import { useCallback } from "react";
import { INACTIVITY_TIMEOUT_MS, clearActivityMarker } from "./inactivity";
import { useInactivityTimeout } from "./useInactivityTimeout";

type Props = {
  /** Override idle window (default 45 minutes). */
  timeoutMs?: number;
};

/**
 * Clerk portals: force re-login after idle inactivity on phone, desktop, or any device.
 * Pair with Clerk Dashboard → Sessions → Inactivity timeout = 45 minutes (Platform + Driver apps).
 */
export function InactivityLogout({ timeoutMs = INACTIVITY_TIMEOUT_MS }: Props) {
  const { isLoaded, isSignedIn } = useAuth();
  const { signOut } = useClerk();

  const onTimeout = useCallback(async () => {
    clearActivityMarker();
    await signOut();
  }, [signOut]);

  useInactivityTimeout({
    enabled: Boolean(isLoaded && isSignedIn),
    timeoutMs,
    onTimeout,
  });

  return null;
}
