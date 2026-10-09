import type { PublishableContent } from "./publishable";

export type SuccessStoryMerchantType =
  | "construction-materials"
  | "electrical-distribution"
  | "plumbing-supply"
  | "coffee-roasters"
  | "pharmacy-medical"
  | "cosmetics";

export type SuccessStory = PublishableContent & {
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
  /** Ops author for E-E-A-T (blogAuthors id) */
  authorId?: string;
  /** Only show metric + Review schema when true (permissioned narrative) */
  permissioned?: boolean;
  /** Customer approval on file before naming or indexing */
  customerApproved?: boolean;
  /** Evidence notes for procurement / editorial review */
  evidenceNotes?: string;
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
    authorId: "sarah-chen",
    permissioned: true,
    customerApproved: true,
    status: "published",
    index: true,
    publishedAt: "2025-11-01",
    updatedAt: "2026-07-01",
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
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes: "Anonymized composite — index when customer approves naming and metrics.",
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
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes: "Anonymized composite — index when customer approves naming and metrics.",
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
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes: "Anonymized composite — index when customer approves naming and metrics.",
  },
  {
    slug: "electrical-wholesaler-overflow-capacity",
    title: "How a Peel electrical wholesaler covered cut-off overflow",
    description:
      "An electrical supply house kept afternoon contractor cut-offs with overflow van capacity — tracking and proof without adding fleet headcount.",
    merchantType: "electrical-distribution",
    industrySlug: "electrical-distribution",
    headline: "Cut-off overflow without hiring another driver",
    challenge:
      "Inside sales volume outran their own routes on peak afternoons. Ad-hoc couriers meant missed contractor windows and no consistent proof for billing disputes.",
    solution:
      "We booked overflow cargo and trade van capacity aligned to their Peel–York cut-offs — same tracking links and photo POD as their primary lanes.",
    outcome:
      "They protected afternoon cut-offs on peak days without permanent headcount. Contractors got ETAs; finance got proof on overflow stops.",
    quote:
      "Overflow had to look like our normal delivery — tracking and proof included. That was non-negotiable.",
    quoteAttribution: "Operations lead, Peel electrical wholesaler",
    outcomeMetric: "Peak cut-offs held without new hires",
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes: "Anonymized composite — index when customer approves naming and metrics.",
  },
  {
    slug: "3pl-warehouse-outbound-peel",
    title: "How a Peel 3PL scaled outbound multi-stop waves",
    description:
      "A GTA 3PL covered merchant outbound multi-stop and peak overflow from Peel docks with vehicle-and-driver capacity and shareable tracking.",
    merchantType: "cosmetics",
    industrySlug: "ecommerce",
    headline: "Outbound waves without permanent fleet capex",
    challenge:
      "Merchant SLAs tightened while dock waves spiked on promotions. Their own vans could not cover multi-stop outbound without overtime risk.",
    solution:
      "We aligned cargo van and box truck capacity to outbound waves — multi-stop density across Toronto and Peel, with tracking merchants could share and POD on every stop.",
    outcome:
      "They cleared peak waves without adding permanent fleet. Account managers stopped fielding ETA chase calls for every brand.",
    quote: "We needed capacity that matched the wave — not another software login.",
    quoteAttribution: "Warehouse ops, Peel 3PL",
    outcomeMetric: "Peak outbound waves covered",
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes:
      "Anonymized composite — index when customer approves naming and metrics. Merchant type mapped to closest publishable category.",
  },
  {
    slug: "plumbing-supply-counter-to-jobsite",
    title: "How a plumbing wholesaler stabilized counter-to-jobsite runs",
    description:
      "A plumbing supply house replaced courier roulette with recurring and same-day capacity for pipe, fixtures, and water heater drops across the GTA.",
    merchantType: "plumbing-supply",
    industrySlug: "plumbing-supply",
    headline: "Trade routes with proof plumbers and PMs trust",
    challenge:
      "Long stock and emergency same-day requests broke their afternoon plan. Couriers varied by day; POD was inconsistent for trade disputes.",
    solution:
      "We set recurring trade-van lanes plus same-day overflow for emergencies — vehicle class matched to pipe and fixtures, photo proof on every jobsite drop.",
    outcome:
      "Counter teams hit more cut-offs with shareable tracking. Billing disputes dropped because proof traveled with every stop.",
    quote: "Plumbers do not wait. We needed capacity that showed up with proof.",
    quoteAttribution: "Counter operations, GTA plumbing wholesaler",
    outcomeMetric: "Recurring + same-day trade lanes",
    authorId: "sarah-chen",
    permissioned: false,
    status: "published",
    index: false,
    evidenceNotes: "Anonymized composite — index when customer approves naming and metrics.",
  },
];

export function getSuccessStoryBySlug(slug: string): SuccessStory | null {
  return SUCCESS_STORIES.find((s) => s.slug === slug) ?? null;
}

/** Public hub + sitemap + SSG — permissioned, indexed, published only. */
export function isPublicSuccessStory(story: SuccessStory): boolean {
  return (
    story.status === "published" &&
    story.index === true &&
    story.permissioned === true &&
    story.customerApproved === true
  );
}

export function listPublicSuccessStories(): SuccessStory[] {
  return SUCCESS_STORIES.filter(isPublicSuccessStory);
}
