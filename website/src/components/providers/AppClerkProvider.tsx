"use client";

import { usePathname } from "next/navigation";
import { publicEnv } from "@/lib/env";
import { isClerkClientShellPath } from "@/lib/clerk-shell";
import ClerkProviderShell from "@/components/providers/ClerkProviderShell";

/**
 * Mount Clerk only on login routes. Import statically (not next/dynamic) so
 * useAuth() on /login never runs outside ClerkProvider during chunk load.
 */
export default function AppClerkProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";

  if (!publicEnv.clerkPublishableKey || !isClerkClientShellPath(pathname)) {
    return <>{children}</>;
  }

  return <ClerkProviderShell>{children}</ClerkProviderShell>;
}
