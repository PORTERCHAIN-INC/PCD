import type { PlatformRole } from "@porterchain/types";

/** Clerk public metadata shape for Porterchain roles (multiple roles supported). */
export interface ClerkPublicMetadata {
  roles?: PlatformRole[];
  userType?: string;
  merchantId?: string;
  driverId?: string;
}

export function mapClerkRoles(metadata: ClerkPublicMetadata | undefined): PlatformRole[] {
  if (!metadata?.roles?.length) {
    return ["visitor"];
  }
  return metadata.roles;
}
