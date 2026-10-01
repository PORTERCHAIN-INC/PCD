/** Public Shopify App Store / OAuth entry points that must not bounce to Clerk sign-in. */

/** True when an install hop landed on our Shopify page, not Shopify's grant screen. */
export function isShopifyAppHomeRedirect(location: string, portalOrigin: string): boolean {
  try {
    const target = new URL(location);
    const home = new URL(portalOrigin);
    return target.origin === home.origin && target.pathname === "/shopify";
  } catch {
    return false;
  }
}

export function isShopifyPublicEntry(
  pathname: string,
  searchParams: { get(name: string): string | null }
): boolean {
  if (pathname !== "/shopify") return false;
  if (searchParams.get("shop") && searchParams.get("hmac")) return true;
  // Post-OAuth callback lands here — requirement 2.3.3 (app UI after permissions).
  if (searchParams.get("connected") === "1") return true;
  return false;
}
