import { publicEnv } from "@/lib/env";
import { embeddedAppHtml, shopifyApiKey } from "@/lib/shopifyEmbed";

export const dynamic = "force-dynamic";

/** Shopify admin iframes this; HTML is hand-built so App Bridge loads first. */
export function GET(req: Request): Response {
  const html = embeddedAppHtml({
    apiKey: shopifyApiKey(new URL(req.url).searchParams.get("app")),
    apiUrl: publicEnv.porterchainApiUrl,
    portalUrl: publicEnv.siteUrl,
    fourClick: process.env.SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED === "true",
  });
  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}
