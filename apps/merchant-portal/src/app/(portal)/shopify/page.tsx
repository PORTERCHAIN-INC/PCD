"use client";

import { Suspense } from "react";
import ShopifyAppClient from "@/components/integrations/ShopifyAppClient";
import { ShopifyOrderSyncPanel } from "@/components/shopify/ShopifyOrderSyncPanel";

export default function ShopifyPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading Shopify…</p>}>
      <ShopifyAppClient />
      <div className="mx-auto mt-8 max-w-5xl">
        <ShopifyOrderSyncPanel hideWhenEmpty />
      </div>
    </Suspense>
  );
}
