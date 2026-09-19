import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { driverPublicEnv, loadMonorepoEnv } from "@porterchain/config/monorepo-env.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: ["@porterchain/ui", "@porterchain/config"],
  env: driverPublicEnv(),
  async rewrites() {
    return [{ source: "/favicon.ico", destination: "/icon.svg" }];
  },
};

export default nextConfig;
