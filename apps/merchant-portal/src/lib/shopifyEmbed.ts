/** Embedded Shopify app (/shopify-app): App Bridge must be the first script in <head>. */

export const EMBEDDED_HEADER = "x-pc-shopify-embedded";
export const APP_BRIDGE_SRC = "https://cdn.shopify.com/shopifycloud/app-bridge.js";

/** Public client id (not the secret), read at request time from the container env. */
export function shopifyApiKey(): string {
  return (process.env.SHOPIFY_API_KEY ?? "").trim();
}
