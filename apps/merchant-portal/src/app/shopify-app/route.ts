import { publicEnv } from "@/lib/env";
import { embeddedAppHtml, shopifyApiKey } from "@/lib/shopifyEmbed";

export const dynamic = "force-dynamic";

/** Shopify admin iframes this; HTML is hand-built so App Bridge loads first. */
export function GET(req: Request): Response {
  const html = embeddedAppHtml({
    apiKey: shopifyApiKey(new URL(req.url).searchParams.get("app")),
    apiUrl: publicEnv.porterchainApiUrl,
    portalUrl: publicEnv.siteUrl,
    // Default ON (Phase 0 G20). Set "false" to fall back to the previously reviewed page.
    fourClick: process.env.SHOPIFY_FOUR_CLICK_ONBOARDING_ENABLED !== "false",
    autoProvision: process.env.SHOPIFY_EMBEDDED_AUTO_PROVISION_ENABLED !== "false",
  });
  return new Response(html, {
    headers: { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" },
  });
}
