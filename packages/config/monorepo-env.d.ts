declare module "@porterchain/config/monorepo-env.mjs" {
  export function loadMonorepoEnv(cwd: string, relativeEnvPath?: string): string;

  export function nextPublicEnv(): Record<string, string | undefined>;

  export function adminPublicEnv(): Record<string, string | undefined>;

  export function customerPublicEnv(): Record<string, string | undefined>;
}
