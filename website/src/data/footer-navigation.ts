export type FooterSectionId = "products" | "solutions" | "company" | "resources" | "legal";

export interface FooterLink {
  id: string;
  href: string;
}

/** Former navbar links live here; navbar keeps Business, Sign in, Quote, Vehicle Partner Portal only. */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  products: [
    { id: "book", href: "/" },
    { id: "business", href: "/business" },
    { id: "customerPortal", href: "__CUSTOMER_PORTAL__" },
    { id: "getQuote", href: "/contact" },
  ],
  solutions: [
    { id: "industry", href: "/industry" },
    { id: "constructionMaterials", href: "/industry/construction-materials" },
    { id: "electricalDistribution", href: "/industry/electrical-distribution" },
    { id: "plumbingSupply", href: "/industry/plumbing-supply" },
    { id: "serviceAreas", href: "/service-areas" },
    { id: "pricing", href: "/pricing" },
    { id: "localDelivery", href: "/local-delivery" },
    { id: "integrations", href: "/integrations" },
    { id: "enterprise", href: "/enterprise" },
    { id: "vanDelivery", href: "/van-delivery" },
    { id: "mediumTruck", href: "/medium-truck" },
  ],
  company: [
    { id: "about", href: "/company" },
    { id: "contact", href: "/contact" },
    { id: "blog", href: "/blog" },
    { id: "careers", href: "/careers" },
    { id: "drive", href: "/vehicle-partner" },
    { id: "vehiclePartnerPortal", href: "/vehicle-partner" },
  ],
  resources: [
    { id: "developers", href: "/developers" },
    { id: "faq", href: "/faq" },
    { id: "guides", href: "/guides" },
    { id: "compare", href: "/compare" },
    { id: "successStories", href: "/success-stories" },
    { id: "onboardingEducation", href: "/onboarding-education" },
    { id: "campaigns", href: "/campaigns" },
    { id: "blogHome", href: "/blog" },
    { id: "logistics", href: "/blog/category/logistics" },
    { id: "constructionBlog", href: "/blog/category/construction" },
    { id: "sameDay", href: "/blog/category/same-day-delivery" },
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
