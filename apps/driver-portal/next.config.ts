import type { NextConfig } from "next";
import { loadMonorepoEnv, nextPublicEnv } from "@porterchain/config/monorepo-env.mjs";

loadMonorepoEnv(process.cwd());

const nextConfig: NextConfig = {
  output: "standalone",
  env: nextPublicEnv(),
  async rewrites() {
    return [{ source: "/favicon.ico", destination: "/icon.svg" }];
  },
};

export default nextConfig;
