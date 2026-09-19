import { Suspense } from "react";
import ShopifyAppClient from "@/components/integrations/ShopifyAppClient";

export default function ShopifyAppPage() {
  return (
    <Suspense fallback={<p className="text-muted">Loading Shopify…</p>}>
      <ShopifyAppClient />
    </Suspense>
  );
}
