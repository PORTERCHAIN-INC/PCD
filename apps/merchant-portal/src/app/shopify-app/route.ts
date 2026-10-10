import { publicEnv } from "@/lib/env";
import { embeddedAppHtml, shopifyApiKey } from "@/lib/shopifyEmbed";

export const dynamic = "force-dynamic";

/** Shopify admin iframes this; HTML is hand-built so App Bridge loads first. */
export function GET(): Response {
  const html = embeddedAppHtml({
    apiKey: shopifyApiKey(),
    apiUrl: publicEnv.porterchainApiUrl,
    portalUrl: publicEnv.siteUrl,
  });
  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}
