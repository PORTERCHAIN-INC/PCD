"use client";

import type { ReactNode } from "react";
import { InactivityLogout } from "./InactivityLogout";
import { AuthProvider } from "./oidc/client";

export type AppAuthProviderProps = {
  children: ReactNode;
  /** Idle logout window; default 45 minutes. */
  inactivityTimeoutMs?: number;
  basePath?: string;
};

/**
 * Keycloak session shell for the portals (L36): session from the app's /auth/session route,
 * plus the 45-minute inactivity re-login (phone + desktop).
 */
export function AppAuthProvider({ children, inactivityTimeoutMs, basePath }: AppAuthProviderProps) {
  return (
    <AuthProvider basePath={basePath}>
      <InactivityLogout timeoutMs={inactivityTimeoutMs} />
      {children}
    </AuthProvider>
  );
}
