"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { publicEnv } from "@/lib/env";

/**
 * Origins Clerk is allowed to redirect to after auth. Must include the host the
 * console is actually served from, otherwise Clerk silently refuses the
 * post-sign-in (and OAuth callback) redirect and the user logs in but never
 * lands on /dashboard. We seed the known production hosts and always add the
 * current browser origin so this works on localhost, preview, and any custom
 * domain without a hardcode.
 */
function allowedRedirectOrigins(): string[] {
  const origins = new Set<string>([
    "https://admin.porterchain.com",
    "https://accounts.admin.porterchain.com",
  ]);
  const configured = publicEnv.siteUrl;
  if (configured) origins.add(configured);
  if (typeof window !== "undefined" && window.location?.origin) {
    origins.add(window.location.origin);
  }
  return Array.from(origins);
}

export default function AppClerkProvider({ children }: { children: React.ReactNode }) {
  if (!publicEnv.clerkPublishableKey) {
    return <>{children}</>;
  }

  return (
    <ClerkProvider
      publishableKey={publicEnv.clerkPublishableKey}
      signInUrl="/sign-in"
      afterSignOutUrl="/sign-in"
      signInFallbackRedirectUrl="/dashboard"
      signInForceRedirectUrl="/dashboard"
      allowedRedirectOrigins={allowedRedirectOrigins()}
    >
      {children}
    </ClerkProvider>
  );
}
