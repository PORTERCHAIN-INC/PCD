export type FooterSectionId = "company" | "resources" | "track" | "legal";

export interface FooterLink {
  id: string;
  href: string;
}

/**
 * Footer IA — formality + SEO crawl paths.
 * Primary buyer/driver journeys live in the navbar hubs.
 */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  company: [
    { id: "about", href: "/company" },
    { id: "contact", href: "/contact" },
    { id: "careers", href: "/careers" },
    { id: "trust", href: "/trust" },
  ],
  resources: [
    { id: "business", href: "/business" },
    { id: "vehiclePartner", href: "/vehicle-partner" },
    { id: "howPorterchainWorks", href: "/how-porterchain-works" },
    { id: "blog", href: "/blog" },
    { id: "faq", href: "/faq" },
    { id: "guides", href: "/guides" },
    { id: "developers", href: "/developers" },
    { id: "customerPortal", href: "__CUSTOMER_PORTAL__" },
  ],
  track: [{ id: "trackShipment", href: "/track" }],
  legal: [
    { id: "privacy", href: "/privacy" },
    { id: "terms", href: "/terms" },
    { id: "cookies", href: "/cookies" },
    { id: "accessibility", href: "/accessibility" },
  ],
};

export const footerSectionOrder: FooterSectionId[] = ["company", "resources", "track", "legal"];
