/**
 * Service intent map — maps commercial delivery intents to canonical routes.
 * Avoid duplicate /services/* pages; extend existing hubs instead.
 */

export type ServiceIntentSlug =
  | "same-day-business-delivery"
  | "urgent-delivery"
  | "scheduled-delivery"
  | "recurring-routes"
  | "fleet-overflow"
  | "dedicated-vehicle"
  | "multi-stop-delivery"
  | "final-mile-delivery"
  | "pallet-delivery"
  | "construction-material-delivery"
  | "commercial-vehicle-on-demand"
  | "api-delivery-booking"
  | "proof-of-delivery"
  | "live-delivery-tracking";

export type ServiceIntentRoute = {
  slug: ServiceIntentSlug;
  /** Primary canonical path segment (locale prefix added at runtime). */
  pathSegment: string;
  faqClusterSlug?: string;
  index: boolean;
};

/** Where each service intent resolves today — no new duplicate routes without IA review. */
export const SERVICE_INTENT_ROUTES: ServiceIntentRoute[] = [
  {
    slug: "same-day-business-delivery",
    pathSegment: "local-delivery",
    faqClusterSlug: "same-day-delivery",
    index: true,
  },
  {
    slug: "urgent-delivery",
    pathSegment: "local-delivery",
    faqClusterSlug: "same-day-delivery",
    index: true,
  },
  {
    slug: "scheduled-delivery",
    pathSegment: "business",
    faqClusterSlug: "delivery-pricing",
    index: true,
  },
  {
    slug: "recurring-routes",
    pathSegment: "guides/merchant-onboarding-guide",
    faqClusterSlug: "onboarding",
    index: true,
  },
  {
    slug: "fleet-overflow",
    pathSegment: "business",
    faqClusterSlug: "fleet-overflow-wholesale-delivery",
    index: true,
  },
  {
    slug: "dedicated-vehicle",
    pathSegment: "business",
    index: true,
  },
  {
    slug: "multi-stop-delivery",
    pathSegment: "how-porterchain-works",
    index: true,
  },
  {
    slug: "final-mile-delivery",
    pathSegment: "local-delivery",
    index: true,
  },
  {
    slug: "pallet-delivery",
    pathSegment: "industry/construction-materials",
    index: true,
  },
  {
    slug: "construction-material-delivery",
    pathSegment: "industry/construction-materials",
    faqClusterSlug: "construction-delivery",
    index: true,
  },
  {
    slug: "commercial-vehicle-on-demand",
    pathSegment: "business",
    index: true,
  },
  {
    slug: "api-delivery-booking",
    pathSegment: "developers",
    faqClusterSlug: "api-integrations",
    index: true,
  },
  {
    slug: "proof-of-delivery",
    pathSegment: "guides/route-and-tracking-overview",
    index: true,
  },
  {
    slug: "live-delivery-tracking",
    pathSegment: "track",
    index: true,
  },
];

export function getServiceIntentRoute(slug: ServiceIntentSlug): ServiceIntentRoute | undefined {
  return SERVICE_INTENT_ROUTES.find((r) => r.slug === slug);
}
