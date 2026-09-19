/** Internal paths only — labels come from `corporate.nav` i18n keys. */

export interface NavbarChildLink {
  id: string;
  href: string;
}

export type NavbarItem =
  | { type: "link"; id: string; href: string }
  | { type: "dropdown"; id: string; href?: string; children: NavbarChildLink[] };

/**
 * Primary chrome: Merchants + Drivers only.
 * Solutions / Vehicles / Resources / Company live in the footer crawl map.
 */
export const navbarNavigation: NavbarItem[] = [
  { type: "link", id: "merchants", href: "/business" },
  { type: "link", id: "drivers", href: "/vehicle-partner" },
];
