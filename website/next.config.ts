import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadMonorepoEnv, websitePublicEnv } from "@porterchain/config/monorepo-env.mjs";
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
  env: websitePublicEnv(),
  async redirects() {
    const legacyMarketRedirects = ["en", "fr"].flatMap((locale) => [
      {
        source: `/ca/${locale === "en" ? "en" : "fr-ca"}/:path*`,
        destination: `/${locale}/:path*`,
        permanent: true,
      },
      {
        source: `/ca/${locale === "en" ? "en" : "fr-ca"}`,
        destination: `/${locale}`,
        permanent: true,
      },
    ]);
    return [
      ...legacyMarketRedirects,
      ...["en", "fr"].flatMap((locale) =>
        removedCorporatePaths.map((path) => ({
          source: `/${locale}/${path}`,
          destination: `/${locale}/business`,
          permanent: true,
        }))
      ),
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: securityHeaders,
      },
    ];
  },
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
    ],
  },
};

export default withNextIntl(nextConfig);
