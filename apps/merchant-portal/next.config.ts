import type { NextConfig } from "next";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { loadMonorepoEnv, merchantPublicEnv } from "@porterchain/config/monorepo-env.mjs";
import { portalSecurityHeaders } from "@porterchain/config/security-headers.mjs";

loadMonorepoEnv(process.cwd());

const monorepoRoot = path.join(path.dirname(fileURLToPath(import.meta.url)), "../..");

/** Shopify Admin embeds /shopify-app — framed only by Shopify, no X-Frame-Options there. */
const shopifyEmbedHeaders = portalSecurityHeaders("merchant", {
  frameAncestors: "https://admin.shopify.com https://*.myshopify.com https://*.shopify.com",
});

const defaultSecurityHeaders = portalSecurityHeaders("merchant");

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
      { source: "/shopify-app", headers: shopifyEmbedHeaders },
      // Everything except the embedded app (negative lookahead so DENY is not merged onto it).
      { source: "/((?!shopify-app$).*)", headers: defaultSecurityHeaders },
      // App subdomains are private tools: never index (Search Console listed sign-in URLs).
      { source: "/(.*)", headers: [{ key: "X-Robots-Tag", value: "noindex, nofollow" }] },
    ];
  },
};

export default nextConfig;
