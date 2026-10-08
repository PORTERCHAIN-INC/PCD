/** Public Shopify App Store / OAuth entry points that must not bounce to Clerk sign-in. */

export function isShopifyPublicEntry(
  pathname: string,
  searchParams: { get(name: string): string | null }
): boolean {
  if (pathname !== "/shopify") return false;
  if (searchParams.get("shop") && searchParams.get("hmac")) return true;
  // Post-OAuth callback lands here — requirement 2.3.3 (app UI after permissions).
  if (searchParams.get("connected") === "1") return true;
  // Failed install step lands here with ?error= — show the reason, not a sign-in wall.
  if (searchParams.get("error")) return true;
  return false;
}
