/**
 * Mobile "Get a price" bar — where it shows. Accepts locale-prefixed (`/en/track`) or stripped paths.
 * Hidden where it would duplicate the page's own price form, or on auth / portal hand-off routes.
 */
const HIDDEN_HEADS = new Set([
  "delivery-cost-calculator",
  "login",
  "sign-in",
  "sign-up",
  "quote",
  "book",
  "newsletter",
  "unsubscribe",
]);

export const HOME_PRICE_ANCHOR_ID = "home-price";

export function isPriceBarHidden(pathname: string): boolean {
  const parts = pathname
    .replace(/^\/+|\/+$/g, "")
    .split("/")
    .filter(Boolean);
  const offset = parts[0] === "en" || parts[0] === "fr" ? 1 : 0;
  const head = parts[offset];
  return head !== undefined && HIDDEN_HEADS.has(head);
}
