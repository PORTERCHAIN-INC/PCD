"use client";

import { ClerkProvider } from "@clerk/nextjs";
import type { ReactNode } from "react";
import { InactivityLogout } from "./InactivityLogout";

export type AppClerkProviderConfig = {
  publishableKey: string;
  signInUrl: string;
  signUpUrl?: string;
  afterSignOutUrl: string;
  fallbackRedirect: string;
  forceRedirect?: string;
  allowedOrigins?: string[];
  /** Idle logout window; default 45 minutes. */
  inactivityTimeoutMs?: number;
};

export type AppClerkProviderProps = AppClerkProviderConfig & {
  children: ReactNode;
};

/**
 * Configurable Clerk shell for portal apps.
 * Website keeps its own path-gated AppClerkProvider — do not use this there.
 * Enforces 45-minute inactivity re-login (phone + desktop).
 */
export function AppClerkProvider({
  children,
  publishableKey,
  signInUrl,
  signUpUrl,
  afterSignOutUrl,
  fallbackRedirect,
  forceRedirect,
  allowedOrigins,
  inactivityTimeoutMs,
}: AppClerkProviderProps) {
  if (!publishableKey) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider
      publishableKey={publishableKey}
      signInUrl={signInUrl}
      signUpUrl={signUpUrl ?? signInUrl}
      afterSignOutUrl={afterSignOutUrl}
      signInFallbackRedirectUrl={fallbackRedirect}
      signInForceRedirectUrl={forceRedirect}
      allowedRedirectOrigins={allowedOrigins}
    >
      <InactivityLogout timeoutMs={inactivityTimeoutMs} />
      {children}
    </ClerkProvider>
  );
}
