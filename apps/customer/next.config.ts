import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { customerPublicEnv, loadMonorepoEnv } from "@porterchain/config/monorepo-env.mjs";
import { portalSecurityHeaders } from "@porterchain/config/security-headers.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: ["@porterchain/ui", "@porterchain/config", "@porterchain/types"],
  reactCompiler: true,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  async headers() {
    return [
      { source: "/(.*)", headers: portalSecurityHeaders("customer") },
      // App subdomains are private tools: never index (Search Console listed sign-in URLs).
      { source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] },
    ];
  },
  env: customerPublicEnv(),
};

export default nextConfig;
