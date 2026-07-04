import type { NextConfig } from "next";
import { existsSync, readFileSync } from "fs";
import path from "path";

/** Load monorepo `env/.env` when present (does not override vars already set). */
function loadMonorepoEnv() {
  const envPath = path.resolve(process.cwd(), "../../env/.env");
  if (!existsSync(envPath)) return;
  for (const line of readFileSync(envPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eq = trimmed.indexOf("=");
    if (eq <= 0) continue;
    const key = trimmed.slice(0, eq).trim();
    if (process.env[key] !== undefined) continue;
    let value = trimmed.slice(eq + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    process.env[key] = value;
  }
}

loadMonorepoEnv();

const googleMapsApiKey =
  process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY?.trim() ||
  process.env.GOOGLE_MAPS_BROWSER_API_KEY?.trim() ||
  "";

const nextConfig: NextConfig = {
  output: "standalone",
  transpilePackages: ["@porterchain/ui"],
  env: {
    NEXT_PUBLIC_GOOGLE_MAPS_API_KEY: googleMapsApiKey,
  },
};

export default nextConfig;
