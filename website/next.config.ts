import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadMonorepoEnv, nextPublicEnv } from "@porterchain/config/monorepo-env.mjs";
import createNextIntlPlugin from "next-intl/plugin";

loadMonorepoEnv(process.cwd(), "../env/.env");

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const removedCorporatePaths = ["platform", "overview", "solutions"] as const;

const securityHeaders = [
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  {
    key: "Permissions-Policy",
    value: "camera=(), microphone=(), geolocation=()",
  },
];

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: ["@porterchain/config"],
  env: {
    ...nextPublicEnv(),
    NEXT_PUBLIC_ADMIN_PORTAL_URL:
      process.env.NEXT_PUBLIC_ADMIN_PORTAL_URL?.trim() || "http://localhost:3002",
    NEXT_PUBLIC_MERCHANT_PORTAL_URL:
      process.env.NEXT_PUBLIC_MERCHANT_PORTAL_URL?.trim() || "http://localhost:3001",
    NEXT_PUBLIC_CUSTOMER_PORTAL_URL:
      process.env.NEXT_PUBLIC_CUSTOMER_PORTAL_URL?.trim() || "http://localhost:3004",
    NEXT_PUBLIC_DRIVER_PORTAL_URL:
      process.env.NEXT_PUBLIC_DRIVER_PORTAL_URL?.trim() || "http://localhost:3003",
  },
  async redirects() {
    return ["en", "fr"].flatMap((locale) =>
      removedCorporatePaths.map((path) => ({
        source: `/${locale}/${path}`,
        destination: `/${locale}/business`,
        permanent: true,
      }))
    );
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
};

export default withNextIntl(nextConfig);
