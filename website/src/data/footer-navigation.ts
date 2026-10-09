export type FooterSectionId = "product" | "solutions" | "integrations" | "resources" | "company";

export interface FooterLink {
  id: string;
  href: string;
}

/**
 * Footer IA — discovery crawl map for everything outside the five navbar links.
 * Merchants (/business) and Drivers (/vehicle-partner) moved here from the navbar
 * (website Phase 1, Oct 2026). Each href appears at most once across all columns.
 */
export const footerNavigation: Record<FooterSectionId, FooterLink[]> = {
  product: [
    { id: "getQuote", href: "/sign-up?intent=quote&from=footer" },
    { id: "calculator", href: "/delivery-cost-calculator" },
    { id: "industriesHub", href: "/delivery" },
    { id: "pricing", href: "/business#pricing" },
    { id: "capabilities", href: "/capabilities" },
    { id: "multiStop", href: "/capabilities/multi-stop-delivery" },
    { id: "recurring", href: "/capabilities/recurring-routes" },
    { id: "brandedTracking", href: "/capabilities/branded-tracking" },
    { id: "deliveryVerification", href: "/capabilities/delivery-verification" },
    { id: "exceptionRecovery", href: "/capabilities/exception-recovery" },
    { id: "multiLocation", href: "/capabilities/multi-location-routing" },
    { id: "inventoryTransfers", href: "/capabilities/inventory-transfers" },
    { id: "returnsRoundTrip", href: "/capabilities/returns-round-trip-capacity" },
    { id: "aiDispatch", href: "/capabilities/ai-dispatch" },
    { id: "platform", href: "/platform" },
  ],
  solutions: [
    { id: "allSolutions", href: "/solutions" },
    { id: "wholesale", href: "/solutions/wholesale" },
    { id: "medical", href: "/solutions/medical" },
    { id: "foodBeverage", href: "/solutions/food-beverage" },
    { id: "construction", href: "/construction" },
    { id: "threePl", href: "/solutions/3pl" },
    { id: "fleetOverflow", href: "/solutions/fleet-overflow" },
    { id: "industries", href: "/business#industries" },
    { id: "serviceAreas", href: "/service-areas" },
    { id: "vehicles", href: "/vehicles" },
    { id: "cargoVan", href: "/cargo-van-delivery" },
    { id: "tradeVan", href: "/trade-van-delivery" },
    { id: "boxTruck", href: "/box-truck-delivery" },
    { id: "pickupTruck", href: "/pickup-truck-delivery" },
  ],
  integrations: [
    { id: "allIntegrations", href: "/integrations" },
    { id: "sms", href: "/integrations-education/sms-status-notifications" },
    { id: "email", href: "/integrations-education/email-status-notifications" },
    { id: "whatsapp", href: "/integrations-education/whatsapp-status-notifications" },
    { id: "webhooks", href: "/integrations-education/webhooks-delivery-events" },
    { id: "api", href: "/integrations-education/api-order-ingestion" },
    { id: "csv", href: "/integrations-education/csv-delivery-uploads" },
    { id: "developers", href: "/developers" },
  ],
  resources: [
    { id: "guides", href: "/guides" },
    {
      id: "capacityNetwork",
      href: "/guides/what-is-a-transportation-capacity-network",
    },
    { id: "sameDay", href: "/guides/same-day-delivery-capacity-gta" },
    {
      id: "courierVsCapacity",
      href: "/guides/choosing-courier-vs-capacity-partner-gta",
    },
    {
      id: "failureModes",
      href: "/guides/delivery-failure-modes-and-recovery",
    },
    { id: "multiLocationGuide", href: "/guides/multi-location-capacity-gta" },
    {
      id: "inventoryTransfersGuide",
      href: "/guides/inventory-transfers-between-locations",
    },
    { id: "fromStore", href: "/guides/same-day-from-store-capacity-gta" },
    { id: "howPorterchainWorks", href: "/how-porterchain-works" },
    { id: "compare", href: "/compare" },
    { id: "blog", href: "/blog" },
    { id: "authors", href: "/authors" },
    { id: "faq", href: "/faq" },
  ],
  company: [
    { id: "about", href: "/company" },
    { id: "merchants", href: "/business" },
    { id: "drivers", href: "/vehicle-partner" },
    { id: "contact", href: "/contact" },
    { id: "careers", href: "/careers" },
    { id: "trust", href: "/trust" },
    { id: "claims", href: "/trust/claims" },
    { id: "trackShipment", href: "/track" },
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
  "product",
  "solutions",
  "integrations",
  "resources",
  "company",
];
