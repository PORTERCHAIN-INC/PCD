import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadMonorepoEnv, merchantPublicEnv } from "@porterchain/config/monorepo-env.mjs";
import { baselineCsp } from "@porterchain/config/security-headers.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

const baseSecurityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
];

/** Shopify Admin embeds /shopify — must not send X-Frame-Options: DENY there. */
const shopifyEmbedHeaders = [
  ...baseSecurityHeaders,
  {
    key: "Content-Security-Policy",
    value: baselineCsp({
      frameAncestors: "https://admin.shopify.com https://*.myshopify.com https://*.shopify.com",
    }),
  },
];

const defaultSecurityHeaders = [
  ...baseSecurityHeaders,
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: baselineCsp() },
];

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: monorepoRoot,
  },
  transpilePackages: ["@porterchain/ui", "@porterchain/config"],
  reactCompiler: true,
  experimental: {
    optimizePackageImports: ["lucide-react"],
  },
  env: merchantPublicEnv(),
  async headers() {
    return [
      { source: "/shopify", headers: shopifyEmbedHeaders },
      { source: "/shopify/:path*", headers: shopifyEmbedHeaders },
      // Everything except exact /shopify (negative lookahead so DENY is not merged onto embed).
      { source: "/((?!shopify(?:/.*)?$).*)", headers: defaultSecurityHeaders },
      // App subdomains are private tools: never index (Search Console listed sign-in URLs).
      { source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] },
    ];
  },
};

export default nextConfig;
