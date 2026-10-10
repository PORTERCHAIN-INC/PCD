import type { Metadata } from "next";
import Script from "next/script";

/** Shopify admin loads this inside its iframe; App Bridge reads the API key meta tag. */
export function generateMetadata(): Metadata {
  return {
    title: "PorterChain Delivery",
    other: { "shopify-api-key": (process.env.SHOPIFY_API_KEY ?? "").trim() },
  };
}

export default function ShopifyEmbeddedLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Script
        src="https://cdn.shopify.com/shopifycloud/app-bridge.js"
        strategy="beforeInteractive"
      />
      {children}
    </>
  );
}
