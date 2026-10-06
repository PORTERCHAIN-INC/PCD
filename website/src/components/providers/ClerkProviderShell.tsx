"use client";

import { ClerkProvider } from "@clerk/nextjs";
import { InactivityLogout } from "@porterchain/auth";
import { publicEnv } from "@/lib/env";

export default function ClerkProviderShell({
  children,
  locale,
}: {
  children: React.ReactNode;
  locale: string;
}) {
  const signInUrl = `/${locale}/login`;
  const signUpUrl = `/${locale}/sign-up`;
  const continueUrl = `/${locale}/login/continue`;

  return (
    <ClerkProvider
      publishableKey={publicEnv.clerkPublishableKey}
      signInUrl={signInUrl}
      signUpUrl={signUpUrl}
      afterSignOutUrl={signInUrl}
      signInFallbackRedirectUrl={continueUrl}
      signUpFallbackRedirectUrl={continueUrl}
    >
      <InactivityLogout />
      {children}
    </ClerkProvider>
  );
}
