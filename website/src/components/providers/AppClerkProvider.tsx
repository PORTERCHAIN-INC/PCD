"use client";

import type { ReactNode } from "react";
import { publicEnv } from "@/lib/env";
import ClerkProviderShell from "@/components/providers/ClerkProviderShell";

/**
 * Clerk wraps the locale tree when a publishable key exists.
 * Locale comes from the server layout (not useLocale) so Cache Components
 * can prerender the shared shell without a client navigation hook.
 */
export default function AppClerkProvider({
  children,
  locale,
}: {
  children: ReactNode;
  locale: string;
}) {
  if (!publicEnv.clerkPublishableKey) {
    return <>{children}</>;
  }

  return <ClerkProviderShell locale={locale}>{children}</ClerkProviderShell>;
}
