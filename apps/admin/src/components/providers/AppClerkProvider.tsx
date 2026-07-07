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
      signInUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? "/sign-in"}
      signUpUrl={process.env.NEXT_PUBLIC_CLERK_SIGN_IN_URL ?? "/sign-in"}
      afterSignOutUrl={process.env.NEXT_PUBLIC_CLERK_AFTER_SIGN_OUT_URL ?? "/sign-in"}
      signInFallbackRedirectUrl={
        process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL ?? "/dashboard"
      }
      signInForceRedirectUrl={
        process.env.NEXT_PUBLIC_CLERK_SIGN_IN_FORCE_REDIRECT_URL ?? "/dashboard"
      }
      allowedRedirectOrigins={["https://admin.porterchain.com"]}
    >
      {children}
    </ClerkProvider>
  );
}
