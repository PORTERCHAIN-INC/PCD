/**
 * Platform provider composition — Clerk is the sole auth provider.
 * Website uses website/src/components/providers/AppClerkProvider.tsx today.
 */
import type { ReactNode } from "react";

export type PlatformProvidersProps = {
  children: ReactNode;
  clerkPublishableKey?: string;
};

export function PlatformProviders({ children }: PlatformProvidersProps) {
  return children;
}
