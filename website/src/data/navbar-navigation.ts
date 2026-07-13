/** Internal paths only — labels come from `corporate.nav` i18n keys. */

export interface NavbarChildLink {
  id: string;
  href: string;
}

export type NavbarItem =
  | { type: "link"; id: string; href: string }
  | { type: "dropdown"; id: string; href?: string; children: NavbarChildLink[] };

export const navbarNavigation: NavbarItem[] = [
  { type: "link", id: "business", href: "/business" },
  {
    type: "dropdown",
    id: "solutions",
    href: "/solutions",
    children: [
      { id: "overview", href: "/solutions" },
      { id: "wholesale", href: "/solutions/wholesale" },
      { id: "medical", href: "/solutions/medical" },
      { id: "foodBeverage", href: "/solutions/food-beverage" },
      { id: "construction", href: "/solutions/construction" },
      { id: "industries", href: "/industry" },
      { id: "serviceAreas", href: "/service-areas" },
    ],
  },
  { type: "link", id: "pricing", href: "/pricing" },
  { type: "link", id: "contact", href: "/contact?intent=quote" },
  {
    type: "dropdown",
    id: "company",
    href: "/company",
    children: [
      { id: "about", href: "/company" },
      { id: "careers", href: "/careers" },
      { id: "contact", href: "/contact" },
      { id: "vehiclePartner", href: "/vehicle-partner" },
    ],
  },
  {
    type: "dropdown",
    id: "resources",
    children: [
      { id: "blog", href: "/blog" },
      { id: "faq", href: "/faq" },
      { id: "guides", href: "/guides" },
      { id: "track", href: "/track" },
      { id: "howItWorks", href: "/how-porterchain-works" },
    ],
  },
];
