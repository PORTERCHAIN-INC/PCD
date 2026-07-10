"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { publicEnv } from "@/lib/env";

export default function ClerkProviderShell({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider
      publishableKey={publicEnv.clerkPublishableKey}
      signInUrl="/login"
      afterSignOutUrl="/login"
      signInFallbackRedirectUrl="/login"
    >
      {children}
    </ClerkProvider>
  );
}
