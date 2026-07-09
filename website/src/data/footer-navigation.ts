export type FooterSectionId = "products" | "solutions" | "company" | "resources" | "legal";

export interface FooterLink {
  id: string;
  href: string;
}

/** Footer IA — grouped by how visitors discover Porterchain (platform → business → industries → company → resources). */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  products: [
    { id: "platform", href: "/platform" },
    { id: "solutions", href: "/solutions" },
    { id: "howItWorks", href: "/guides/how-porterchain-works" },
    { id: "integrations", href: "/integrations" },
    { id: "developers", href: "/developers" },
    { id: "track", href: "/track" },
  ],
  solutions: [
    { id: "business", href: "/business" },
    { id: "enterprise", href: "/enterprise" },
    { id: "pricing", href: "/pricing" },
    { id: "trust", href: "/trust" },
    { id: "getQuote", href: "/contact?intent=quote" },
    { id: "customerPortal", href: "__CUSTOMER_PORTAL__" },
  ],
  company: [
    { id: "industry", href: "/industry" },
    { id: "constructionMaterials", href: "/industry/construction-materials" },
    { id: "electricalDistribution", href: "/industry/electrical-distribution" },
    { id: "plumbingSupply", href: "/industry/plumbing-supply" },
    { id: "serviceAreas", href: "/service-areas" },
    { id: "localDelivery", href: "/local-delivery" },
    { id: "vanDelivery", href: "/van-delivery" },
  ],
  resources: [
    { id: "about", href: "/company" },
    { id: "contact", href: "/contact" },
    { id: "careers", href: "/careers" },
    { id: "vehiclePartner", href: "/vehicle-partner" },
    { id: "blog", href: "/blog" },
    { id: "faq", href: "/faq" },
    { id: "guides", href: "/guides" },
    { id: "compare", href: "/compare" },
    { id: "successStories", href: "/success-stories" },
    { id: "onboardingEducation", href: "/guides" },
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
