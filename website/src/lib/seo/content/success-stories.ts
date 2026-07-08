/**
 * Merchant success stories framework.
 * Construction trades listed first — primary marketing vertical.
 */

export type SuccessStoryMerchantType =
  | "construction-materials"
  | "electrical-distribution"
  | "plumbing-supply"
  | "coffee-roasters"
  | "pharmacy-medical"
  | "cosmetics";

export type SuccessStory = {
  slug: string;
  title: string;
  description: string;
  merchantType: SuccessStoryMerchantType;
  industrySlug: string;
  headline: string;
  challenge: string;
  solution: string;
  outcome: string;
  quote?: string;
  quoteAttribution?: string;
  outcomeMetric?: string;
};

export const MERCHANT_TYPE_LABELS: Record<SuccessStoryMerchantType, string> = {
  "construction-materials": "Construction materials",
  "electrical-distribution": "Electrical distribution",
  "plumbing-supply": "Plumbing supply",
  "coffee-roasters": "Coffee roasters",
  "pharmacy-medical": "Pharmacies",
  cosmetics: "Beauty brands",
};

export const SUCCESS_STORIES: SuccessStory[] = [
  {
    slug: "construction-distributor-jobsite-delivery",
    title: "How a GTA building supply distributor scaled jobsite delivery",
    description:
      "A regional building materials distributor replaced ad-hoc couriers with recurring box truck routes to job sites across the GTA — with proof of delivery on every drop.",
    merchantType: "construction-materials",
    industrySlug: "construction-materials",
    headline: "Recurring jobsite delivery without adding fleet",
    challenge:
      "They were delivering lumber, drywall, and fixtures to dozens of active job sites each week. Ad-hoc couriers meant missed windows, no proof for GC disputes, and ops staff chasing drivers for updates.",
    solution:
      "We aligned 16 ft box truck routes to their daily dispatch list — fixed time windows, site access notes, and photo proof on every delivery. One dashboard for inside sales and dispatch.",
    outcome:
      "They scaled to 40+ weekly jobsite drops with one delivery partner. Fewer site delays, clear POD for billing, and dispatch stopped juggling multiple courier apps.",
    quote:
      "We needed pallet delivery to sites with proof our GCs would accept. Porterchain made it repeatable.",
    quoteAttribution: "Operations Manager, GTA building supply distributor",
    outcomeMetric: "40+ jobsite drops per week",
  },
  {
    slug: "coffee-roaster-wholesale-delivery",
    title: "How a Toronto coffee roaster scaled wholesale delivery",
    description:
      "A specialty roaster scaled delivery to 50+ cafés across the GTA with recurring routes and same-day freshness. No fleet, one partner.",
    merchantType: "coffee-roasters",
    industrySlug: "coffee-roasters",
    headline: "Scaling wholesale delivery without the ops headache",
    challenge:
      "They needed to get fresh roasted coffee to cafés and subscribers across the GTA on a predictable schedule, without running their own fleet or juggling multiple couriers.",
    solution:
      "We aligned recurring routes and same-day windows to their roast cycle. One partner for wholesale drops and subscription boxes, with tracking so cafés and subscribers could see ETAs.",
    outcome:
      "They scaled to 50+ cafés and growing subscription volume with a single delivery partner. Operations stayed focused on roasting; we handled the last mile.",
    quote:
      "We needed one partner who could do recurring routes and same-day when it mattered. Porterchain made it simple.",
    quoteAttribution: "Operations, Toronto roastery",
    outcomeMetric: "50+ cafés served",
  },
  {
    slug: "pharmacy-patient-delivery",
    title: "Pharmacy delivery that keeps compliance and speed",
    description:
      "A local pharmacy scaled prescription and patient delivery across the region with trackable, compliant logistics. Same-day and recurring routes.",
    merchantType: "pharmacy-medical",
    industrySlug: "pharmacy-medical",
    headline: "Reliable patient delivery without adding fleet",
    challenge:
      "They needed to extend delivery to patients and partner clinics without compromising compliance or adding vehicles and drivers in-house.",
    solution:
      "We set up recurring and on-demand routes with full tracking and chain-of-custody visibility. Same-day options where needed, with one dashboard for dispatch and status.",
    outcome:
      "They expanded delivery coverage and kept compliance. Patients and clinics get reliable ETAs; the pharmacy team has one place to see every run.",
    quote:
      "We needed a delivery partner we could trust with prescriptions. Tracking and consistency were non-negotiable.",
    quoteAttribution: "Pharmacy operations, Ontario",
    outcomeMetric: "Same-day across GTA",
  },
  {
    slug: "beauty-brand-d2c-fulfillment",
    title: "How a beauty brand scaled D2C and subscription fulfillment",
    description:
      "A cosmetics brand scaled D2C and subscription box fulfillment with local delivery across Ontario. One partner for recurring and same-day.",
    merchantType: "cosmetics",
    industrySlug: "cosmetics",
    headline: "D2C and subscription fulfillment that scales",
    challenge:
      "They were outgrowing ad-hoc couriers and needed predictable, trackable delivery for D2C and subscription customers without building in-house fulfillment.",
    solution:
      "We aligned capacity to their volume and zones. Recurring pickup and delivery with careful handling, plus same-day for promotions. Every shipment has a tracking link for customers.",
    outcome:
      "They scaled subscription and D2C volume with one delivery partner. Fewer missed windows and consistent customer experience.",
    quote:
      "Having one partner for recurring and same-day took the logistics guesswork out of growth.",
    quoteAttribution: "Operations, beauty brand",
    outcomeMetric: "Recurring + same-day in Ontario",
  },
];

export function getSuccessStoryBySlug(slug: string): SuccessStory | null {
  return SUCCESS_STORIES.find((s) => s.slug === slug) ?? null;
}

export function getSuccessStoriesByMerchantType(type: SuccessStoryMerchantType): SuccessStory[] {
  return SUCCESS_STORIES.filter((s) => s.merchantType === type);
}

export function getAllSuccessStorySlugs(): string[] {
  return SUCCESS_STORIES.map((s) => s.slug);
}
