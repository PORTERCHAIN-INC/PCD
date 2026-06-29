export type FooterSectionId = "products" | "company" | "resources";

export interface FooterLink {
  id: string;
  href: string;
}

export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  products: [
    { id: "book", href: "/" },
    { id: "business", href: "/business" },
  ],
  company: [
    { id: "about", href: "/company" },
    { id: "careers", href: "/careers" },
    { id: "blog", href: "/blog" },
    { id: "contact", href: "/contact" },
  ],
  resources: [
    { id: "blogHome", href: "/blog" },
    { id: "logistics", href: "/blog/category/logistics" },
    { id: "routeOptimization", href: "/blog/category/route-optimization" },
    { id: "supplyChain", href: "/blog/category/supply-chain" },
    { id: "sameDay", href: "/blog/category/same-day-delivery" },
  ],
};

export const footerSectionOrder: FooterSectionId[] = [
  "products",
  "company",
  "resources",
];
