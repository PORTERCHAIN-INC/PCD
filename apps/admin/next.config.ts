import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { adminPublicEnv, loadMonorepoEnv } from "@porterchain/config/monorepo-env.mjs";
import { portalSecurityHeaders } from "@porterchain/config/security-headers.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

const nextConfig: NextConfig = {
  // Local stack opened by LAN IP / 127.0.0.1: without this `next dev` blocks HMR and never hydrates.
  allowedDevOrigins: (process.env.NEXT_ALLOWED_DEV_ORIGINS ?? "")
    .split(",")
    .map((o) => o.trim())
    .filter(Boolean),
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: [
    "@porterchain/ui",
    "@porterchain/config",
    "@porterchain/types",
    "@porterchain/web-push",
  ],
  reactCompiler: true,
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
  async headers() {
    return [
      { source: "/(.*)", headers: portalSecurityHeaders("admin") },
      // App subdomains are private tools: never index (Search Console listed sign-in URLs).
      { source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] },
    ];
  },
  env: adminPublicEnv(),
};

export default nextConfig;
