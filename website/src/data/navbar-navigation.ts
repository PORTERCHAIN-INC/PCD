/** Internal paths only — labels come from `corporate.nav` i18n keys. */

export interface NavbarChildLink {
  id: string;
  href: string;
}

export type NavbarItem =
  | { type: "link"; id: string; href: string }
  | { type: "dropdown"; id: string; href?: string; children: NavbarChildLink[] };

/**
 * Primary chrome (website Phase 1, Oct 2026): five top links — Price, Industries, Track,
 * Shopify app + "Sign in" (rendered by SiteNavbarAuth, not listed here).
 * Merchants (/business), Drivers (/vehicle-partner) and every other destination live in the
 * footer crawl map (see footer-navigation.ts).
 *
 * "Shopify app" points at the public Shopify-merchants page: the app itself sits behind
 * merchant-portal login and has no public App Store listing yet (swap the href when it does).
 */
export const navbarNavigation: NavbarItem[] = [
  { type: "link", id: "price", href: "/delivery-cost-calculator" },
  { type: "link", id: "industries", href: "/delivery" },
  { type: "link", id: "track", href: "/track" },
  { type: "link", id: "shopifyApp", href: "/delivery/shopify-merchants" },
];
