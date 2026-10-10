import type { Metadata } from "next";

// App Bridge + the shopify-api-key meta are rendered first in <head> by the root
// layout (middleware flags /shopify-app). Request-time env, never build-time.
export const dynamic = "force-dynamic";

export const metadata: Metadata = { title: "PorterChain Delivery" };

export default function ShopifyEmbeddedLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
