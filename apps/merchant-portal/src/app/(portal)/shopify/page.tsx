import { Suspense } from "react";
import { redirect } from "next/navigation";
import { request as httpsRequest } from "node:https";
import ShopifyAppClient from "@/components/integrations/ShopifyAppClient";
import { publicEnv } from "@/lib/env";
import { isShopifyAppHomeRedirect } from "@/lib/shopifyPublicEntry";

type Search = Record<string, string | string[] | undefined>;

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? "") : (value ?? "");
}

/** Read Location without following — Next fetch(redirect:manual) often hides cross-origin headers. */
function readRedirectLocation(url: string): Promise<string | null> {
  return new Promise((resolve) => {
    const req = httpsRequest(url, { method: "GET" }, (res) => {
      const location = res.headers.location ?? null;
      res.resume();
      resolve(location);
    });
    req.on("error", () => resolve(null));
    req.setTimeout(8_000, () => {
      req.destroy();
      resolve(null);
    });
    req.end();
  });
}

export default async function ShopifyAppPage({ searchParams }: { searchParams: Promise<Search> }) {
  const params = await searchParams;
  const shop = first(params.shop);
  const hmac = first(params.hmac);
  if (shop && hmac) {
    const qs = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === "string") qs.set(key, value);
      else if (Array.isArray(value)) {
        for (const item of value) qs.append(key, item);
      }
    }
    const installUrl = `${publicEnv.porterchainApiUrl}/v1/integrations/shopify/install?${qs.toString()}`;
    const location = await readRedirectLocation(installUrl);
    // Never follow Shopify's grant screen. Only continue onto our own app page.
    if (location && isShopifyAppHomeRedirect(location, publicEnv.siteUrl)) {
      redirect(location);
    }
  }

  return (
    <Suspense fallback={<p className="text-muted">Loading Shopify…</p>}>
      <ShopifyAppClient />
    </Suspense>
  );
}
