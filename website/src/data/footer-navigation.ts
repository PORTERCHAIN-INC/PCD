export type FooterSectionId = "products" | "solutions" | "company" | "resources" | "legal";

export interface FooterLink {
  id: string;
  href: string;
}

/** Footer IA — grouped around buying capacity, service fit, and company trust. */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  products: [
    { id: "business", href: "/business" },
    { id: "solutions", href: "/solutions" },
    { id: "howItWorks", href: "/how-porterchain-works" },
    { id: "pricing", href: "/pricing" },
    { id: "getQuote", href: "/contact?intent=quote" },
    { id: "track", href: "/track" },
  ],
  solutions: [
    { id: "industry", href: "/industry" },
    { id: "constructionMaterials", href: "/industry/construction-materials" },
    { id: "electricalDistribution", href: "/industry/electrical-distribution" },
    { id: "plumbingSupply", href: "/industry/plumbing-supply" },
    { id: "serviceAreas", href: "/service-areas" },
    { id: "enterprise", href: "/enterprise" },
  ],
  company: [
    { id: "about", href: "/company" },
    { id: "contact", href: "/contact" },
    { id: "careers", href: "/careers" },
    { id: "vehiclePartner", href: "/vehicle-partner" },
    { id: "trust", href: "/trust" },
  ],
  resources: [
    { id: "blog", href: "/blog" },
    { id: "faq", href: "/faq" },
    { id: "guides", href: "/guides" },
    { id: "platform", href: "/platform" },
    { id: "integrations", href: "/integrations" },
    { id: "developers", href: "/developers" },
    { id: "customerPortal", href: "__CUSTOMER_PORTAL__" },
  ],
  legal: [
    { id: "privacy", href: "/privacy" },
    { id: "terms", href: "/terms" },
    { id: "cookies", href: "/cookies" },
  ],
};

export const footerSectionOrder: FooterSectionId[] = [
  "products",
  "solutions",
  "company",
  "resources",
  "legal",
];
