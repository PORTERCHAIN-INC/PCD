"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { publicEnv } from "@/lib/env";

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
    >
      {children}
    </ClerkProvider>
  );
}
