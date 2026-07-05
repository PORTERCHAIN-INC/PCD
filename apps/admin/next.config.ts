import type { NextConfig } from "next";
import { adminPublicEnv, loadMonorepoEnv } from "@porterchain/config/monorepo-env.mjs";

loadMonorepoEnv(process.cwd());

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@porterchain/ui"],
  env: adminPublicEnv(),
};

export default nextConfig;
