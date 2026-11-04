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
  distDir: process.env.NEXT_DIST_DIR || ".next",
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
  // Doc 75 §3: old routes 308 to their new place for one release.
  async redirects() {
    return [
      { source: "/dashboard", destination: "/today", permanent: true },
      { source: "/system-health", destination: "/system", permanent: true },
      { source: "/system-tests", destination: "/system?tab=tests", permanent: true },
      { source: "/admin/system-health", destination: "/system", permanent: true },
      { source: "/admin/system-tests", destination: "/system?tab=tests", permanent: true },
    ];
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
