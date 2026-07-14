"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { publicEnv } from "@/lib/env";

function allowedRedirectOrigins(): string[] {
  const origins = new Set<string>(["https://admin.porterchain.com"]);
  const site = (process.env.NEXT_PUBLIC_SITE_URL ?? "").trim();
  if (site) origins.add(site.replace(/\/$/, ""));
  if (process.env.NEXT_PUBLIC_APP_ENV === "local" || process.env.NODE_ENV === "development") {
    origins.add("http://localhost:3002");
    origins.add("http://127.0.0.1:3002");
  }
  return [...origins];
}

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
      allowedRedirectOrigins={allowedRedirectOrigins()}
    >
      {children}
    </ClerkProvider>
  );
}
