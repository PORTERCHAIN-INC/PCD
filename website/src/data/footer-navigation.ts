import { DELIVERY_VERTICALS } from "@/lib/seo/delivery-programmatic";

export type FooterSectionId = "services" | "industries" | "company" | "support" | "legal";

export interface FooterLink {
  id: string;
  href: string;
  /** Label comes from the delivery-programmatic data instead of siteFooter messages. */
  label?: string;
}

/**
 * Footer IA (Oct 2026 consolidation). Only pages that help a visitor get a price, book, trust
 * us, or find what they came for. Evidence + keep/merge/remove decisions:
 * tmp/website-footer/keep-remove.md. Merged pages 301 via lib/seo/redirects.ts
 * (footerConsolidationRedirects). Each href appears at most once across all columns.
 */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  services: [
    { id: "price", href: "/delivery-cost-calculator" },
    { id: "book", href: "/sign-up?intent=quote&from=footer" },
    { id: "business", href: "/business" },
    { id: "track", href: "/track" },
    { id: "serviceAreas", href: "/service-areas" },
    { id: "vehicles", href: "/vehicles" },
    { id: "howItWorks", href: "/platform" },
    { id: "integrations", href: "/integrations" },
    { id: "developers", href: "/developers" },
  ],
  industries: [
    { id: "allIndustries", href: "/delivery" },
    ...DELIVERY_VERTICALS.map((v) => ({
      id: v.slug,
      href: `/delivery/${v.slug}`,
      label: v.name,
    })),
  ],
  company: [
    { id: "about", href: "/company" },
    { id: "trust", href: "/trust" },
    { id: "drivers", href: "/vehicle-partner" },
    { id: "careers", href: "/careers" },
    { id: "blog", href: "/blog" },
  ],
  support: [
    { id: "contact", href: "/contact" },
    { id: "faq", href: "/faq" },
    { id: "guides", href: "/guides" },
    { id: "claims", href: "/trust/claims" },
    { id: "merchantPortal", href: "__MERCHANT_PORTAL__" },
    { id: "driverPortal", href: "__DRIVER_PORTAL__" },
  ],
  legal: [
    { id: "privacy", href: "/privacy" },
    { id: "terms", href: "/terms" },
    { id: "cookies", href: "/cookies" },
    { id: "accessibility", href: "/accessibility" },
  ],
};

/** Guard: every href must be unique across the footer. */
export function assertUniqueFooterHrefs(
  nav: Record<FooterSectionId, FooterLink[]> = footerNavigation
): void {
  const seen = new Map<string, string>();
  for (const [section, links] of Object.entries(nav)) {
    for (const link of links) {
      const prev = seen.get(link.href);
      if (prev) {
        throw new Error(`Duplicate footer href ${link.href} in ${prev} and ${section}`);
      }
      seen.set(link.href, section);
    }
  }
}

export const footerSectionOrder: FooterSectionId[] = [
  "services",
  "industries",
  "company",
  "support",
  "legal",
];
