"use client";

import { useAuth } from "./oidc/client";
import { useCallback } from "react";
import { INACTIVITY_TIMEOUT_MS, clearActivityMarker } from "./inactivity";
import { useInactivityTimeout } from "./useInactivityTimeout";

type Props = {
  /** Override idle window (default 45 minutes). */
  timeoutMs?: number;
};

/**
 * Portals: force re-login after idle inactivity on phone, desktop, or any device.
 * Pair with the Keycloak realm SSO idle timeout (45 minutes).
 */
export function InactivityLogout({ timeoutMs = INACTIVITY_TIMEOUT_MS }: Props) {
  const { isLoaded, isSignedIn, signOut } = useAuth();

  const onTimeout = useCallback(async () => {
    clearActivityMarker();
    signOut();
  }, [signOut]);

  useInactivityTimeout({
    enabled: Boolean(isLoaded && isSignedIn),
    timeoutMs,
    onTimeout,
  });

  return null;
}
