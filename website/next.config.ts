import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadMonorepoEnv, websitePublicEnv } from "@porterchain/config/monorepo-env.mjs";
import createNextIntlPlugin from "next-intl/plugin";
import { toNextRedirects } from "./src/lib/seo/redirects";

loadMonorepoEnv(process.cwd(), "../env/.env");

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

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
  transpilePackages: ["@porterchain/config", "@porterchain/types", "@porterchain/ui"],
  reactCompiler: true,
  cacheComponents: true,
  env: websitePublicEnv(),
  async redirects() {
    return toNextRedirects();
  },
  async headers() {
    return [
      {
        source: "/sitemap.xml",
        headers: [
          {
            key: "Content-Type",
            value: "application/xml; charset=utf-8",
          },
          {
            key: "Cache-Control",
            value: "public, max-age=3600, s-maxage=86400, stale-while-revalidate=604800",
          },
        ],
      },
      {
        source: "/robots.txt",
        headers: [
          {
            key: "Content-Type",
            value: "text/plain; charset=utf-8",
          },
          {
            key: "Cache-Control",
            value: "public, max-age=3600, s-maxage=86400",
          },
        ],
      },
      {
        source: "/(.*)",
        headers: [
          ...securityHeaders,
          {
            key: "Link",
            value: "<https://images.unsplash.com>; rel=preconnect; crossorigin",
          },
        ],
      },
    ];
  },
  images: {
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86_400,
    // Prefer sharper defaults when quality prop is omitted by callers.
    // (SiteImage still sets quality explicitly for brand assets.)
    deviceSizes: [640, 750, 828, 1080, 1200, 1920, 2048, 2560, 3840, 5120],
    imageSizes: [16, 32, 48, 64, 96, 128, 256, 384, 512],
    qualities: [75, 80, 90, 95, 100],
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.unsplash.com",
        pathname: "/**",
      },
      {
        protocol: "http",
        hostname: "localhost",
        port: "8001",
        pathname: "/v1/public/blog/media/**",
      },
      {
        protocol: "https",
        hostname: "porterchain.com",
        pathname: "/v1/public/blog/media/**",
      },
      {
        protocol: "https",
        hostname: "api.porterchain.com",
        pathname: "/v1/public/blog/media/**",
      },
    ],
  },
};

export default withNextIntl(nextConfig);
