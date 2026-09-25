import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { adminPublicEnv, loadMonorepoEnv } from "@porterchain/config/monorepo-env.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: ["@porterchain/ui", "@porterchain/config", "@porterchain/types"],
  experimental: {
    optimizePackageImports: ["lucide-react", "framer-motion"],
  },
  env: adminPublicEnv(),
};

export default nextConfig;
