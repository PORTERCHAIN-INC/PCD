"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { useLocale } from "next-intl";
import { publicEnv } from "@/lib/env";

export default function ClerkProviderShell({ children }: { children: React.ReactNode }) {
  const locale = useLocale();
  const signInUrl = `/${locale}/login`;
  const continueUrl = `/${locale}/login/continue`;

  return (
    <ClerkProvider
      publishableKey={publicEnv.clerkPublishableKey}
      signInUrl={signInUrl}
      afterSignOutUrl={signInUrl}
      signInFallbackRedirectUrl={continueUrl}
      signUpFallbackRedirectUrl={continueUrl}
    >
      {children}
    </ClerkProvider>
  );
}
