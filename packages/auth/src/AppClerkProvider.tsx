"use client";

import { ClerkProvider } from "@clerk/nextjs";
import type { ReactNode } from "react";

export type AppClerkProviderConfig = {
  publishableKey: string;
  signInUrl: string;
  signUpUrl?: string;
  afterSignOutUrl: string;
  fallbackRedirect: string;
  forceRedirect?: string;
  allowedOrigins?: string[];
};

export type AppClerkProviderProps = AppClerkProviderConfig & {
  children: ReactNode;
};

/**
 * Configurable Clerk shell for portal apps.
 * Website keeps its own path-gated AppClerkProvider — do not use this there.
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
      {children}
    </ClerkProvider>
  );
}
