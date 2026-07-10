"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { publicEnv } from "@/lib/env";
import { isClerkClientShellPath } from "@/lib/clerk-shell";

const ClerkProviderShell = dynamic(() => import("@/components/providers/ClerkProviderShell"), {
  ssr: false,
});

export default function AppClerkProvider({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";

  if (!publicEnv.clerkPublishableKey || !isClerkClientShellPath(pathname)) {
    return <>{children}</>;
  }

  return <ClerkProviderShell>{children}</ClerkProviderShell>;
}
