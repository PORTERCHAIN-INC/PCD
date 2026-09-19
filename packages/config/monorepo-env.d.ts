declare module "@porterchain/config/monorepo-env.mjs" {
  export const CLERK_PORTALS: readonly ["customer", "merchant", "admin", "driver"];

  export function loadMonorepoEnv(cwd: string, relativeEnvPath?: string): string;

  export function pick(...keys: string[]): string;

  export function clerkKeysForPortal(portal: string): {
    publishable: string;
    secret: string;
    jwks: string;
  };

  export function portalPublicEnv(
    portal: string,
    extras?: Record<string, string | undefined>
  ): Record<string, string | undefined>;

  export function nextPublicEnv(): Record<string, string | undefined>;

  export function websitePublicEnv(): Record<string, string | undefined>;

  export function adminPublicEnv(): Record<string, string | undefined>;

  export function merchantPublicEnv(): Record<string, string | undefined>;

  export function driverPublicEnv(): Record<string, string | undefined>;

  export function customerPublicEnv(): Record<string, string | undefined>;
}
