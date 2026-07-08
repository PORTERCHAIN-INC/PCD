/**
 * Article topics for the logistics content framework.
 * Used to drive internal links from articles to industry, service area, and city-industry pages.
 * See PORTERCHAIN-LOGISTICS-ARTICLES-FRAMEWORK.md for pillar definitions and rules.
 */

/** Content pillar for logistics articles. */
export type ArticlePillar =
  | "delivery-strategies-local-brands"
  | "courier-cost-optimization"
  | "last-mile-insights"
  | "industry-delivery-guides";

/** Suggested internal link targets for an article. All slugs match existing routes. */
export type ArticleTopicLinks = {
  /** Link to industry index (industry). */
  industryIndex?: boolean;
  /** Industry slugs for industry/[slug]. */
  industrySlugs?: string[];
  /** Link to service areas index (service-areas). */
  serviceAreasIndex?: boolean;
  /** Service area slugs for service-areas/[slug]. */
  serviceAreaSlugs?: string[];
  /** [industrySlug, serviceAreaSlug] for delivery/[industry]/[city]. */
  deliveryPairs?: [string, string][];
  /** Campaign slugs for campaigns/[slug]. */
  campaignSlugs?: string[];
  /** Suggest primary CTA: merchant, track, support. */
  primaryCta?: "merchant" | "track" | "support";
};

export type ArticleTopic = {
  /** URL-safe slug for the article (e.g. blog/[slug]). */
  slug: string;
  pillar: ArticlePillar;
  /** Short title for listings and nav. */
  title: string;
  /** One-line description for cards and meta. */
  description: string;
  /** Internal links to include when rendering this article. */
  links: ArticleTopicLinks;
};

/** All defined article topics. Add new ones here when creating articles. */
export const ARTICLE_TOPICS: ArticleTopic[] = [
  // —— Delivery strategies for local brands ——
  {
    slug: "choose-local-delivery-partner-gta-ontario",
    pillar: "delivery-strategies-local-brands",
    title: "How to choose a local delivery partner (GTA & Ontario)",
    description:
      "Checklist for capacity, SLA, tracking, and coverage when selecting a courier in the GTA and Ontario.",
    links: {
      serviceAreasIndex: true,
      serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "same-day-delivery-local-brands",
    pillar: "delivery-strategies-local-brands",
    title: "Same-day delivery for local brands: when it pays off",
    description: "When to offer same-day vs next-day and how it affects cost and conversion.",
    links: {
      serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "scaling-subscription-delivery",
    pillar: "delivery-strategies-local-brands",
    title: "Scaling subscription delivery without the logistics headache",
    description: "Recurring routes, batch windows, and partner selection for subscription and D2C.",
    links: {
      industrySlugs: ["coffee-roasters", "cosmetics"],
      campaignSlugs: ["recurring-delivery"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "local-delivery-strategy-five-decisions",
    pillar: "delivery-strategies-local-brands",
    title: "Building a local delivery strategy: 5 decisions that matter",
    description: "Geography, frequency, vehicle type, tracking, and partner vs in-house.",
    links: {
      industryIndex: true,
      industrySlugs: ["coffee-roasters", "pharmacy-medical"],
      serviceAreaSlugs: ["toronto", "kitchener-waterloo"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "local-delivery-gta-merchants",
    pillar: "delivery-strategies-local-brands",
    title: "Local delivery in the GTA: what merchants need to know",
    description: "Coverage, density, and same-day feasibility across the Greater Toronto Area.",
    links: {
      serviceAreasIndex: true,
      serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
      industryIndex: true,
      primaryCta: "merchant",
    },
  },
  // —— Courier cost optimization ——
  {
    slug: "reduce-courier-costs",
    pillar: "courier-cost-optimization",
    title: "5 ways to reduce courier costs without cutting service",
    description: "Consolidation, time windows, recurring routes, vehicle fit, and visibility.",
    links: {
      industryIndex: true,
      primaryCta: "merchant",
    },
  },
  {
    slug: "recurring-vs-on-demand-delivery-cost",
    pillar: "courier-cost-optimization",
    title: "Recurring delivery vs on-demand: cost and when to use each",
    description: "Compare use cases and cost for recurring vs on-demand last-mile.",
    links: {
      campaignSlugs: ["recurring-delivery"],
      industrySlugs: ["coffee-roasters", "pharmacy-medical"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "benchmark-last-mile-spend",
    pillar: "courier-cost-optimization",
    title: "How to benchmark your last-mile delivery spend",
    description: "What to measure and how to compare your delivery costs.",
    links: {
      serviceAreasIndex: true,
      serviceAreaSlugs: ["toronto", "kitchener-waterloo"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "predictable-delivery-costs-ontario",
    pillar: "courier-cost-optimization",
    title: "Predictable delivery costs for Ontario merchants",
    description: "Transparent pricing and no surprise fees across Ontario.",
    links: {
      serviceAreasIndex: true,
      serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london"],
      primaryCta: "merchant",
    },
  },
  // —— Last-mile delivery insights ——
  {
    slug: "last-mile-for-local-merchants",
    pillar: "last-mile-insights",
    title: "What “last-mile” actually means for local merchants",
    description: "Definition, why it’s hard, and how partners help.",
    links: {
      industryIndex: true,
      serviceAreasIndex: true,
      primaryCta: "merchant",
    },
  },
  {
    slug: "same-day-delivery-toronto-gta-guide",
    pillar: "last-mile-insights",
    title: "Same-day delivery in Toronto and the GTA: a practical guide",
    description: "Cutoffs, zones, and reliability for same-day in the GTA.",
    links: {
      serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
      primaryCta: "track",
    },
  },
  {
    slug: "delivery-visibility-eta-tracking",
    pillar: "last-mile-insights",
    title: "Why delivery visibility matters (and how to get it)",
    description: "ETA, status, and exceptions for operations and customers.",
    links: {
      industrySlugs: ["pharmacy-medical"],
      primaryCta: "track",
    },
  },
  {
    slug: "same-day-next-day-ontario",
    pillar: "last-mile-insights",
    title: "Same-day and next-day delivery across Ontario",
    description: "Where we offer same-day and next-day across Ontario.",
    links: {
      serviceAreaSlugs: [
        "toronto",
        "mississauga",
        "oshawa",
        "kitchener-waterloo",
        "london",
        "niagara",
      ],
      primaryCta: "merchant",
    },
  },
  {
    slug: "delivery-reliability-slas",
    pillar: "last-mile-insights",
    title: "Delivery reliability: how to set and hit SLAs",
    description: "SLA design and partner selection for consistent delivery.",
    links: {
      industryIndex: true,
      primaryCta: "support",
    },
  },
  // —— Industry delivery guides ——
  {
    slug: "coffee-roaster-delivery-guide",
    pillar: "industry-delivery-guides",
    title: "Coffee roaster delivery: wholesale and subscription",
    description: "Routes, packaging, and same-day for cafés and wholesale.",
    links: {
      industrySlugs: ["coffee-roasters"],
      serviceAreaSlugs: ["toronto", "kitchener-waterloo"],
      deliveryPairs: [
        ["coffee-roasters", "toronto"],
        ["coffee-roasters", "kitchener-waterloo"],
      ],
      primaryCta: "merchant",
    },
  },
  {
    slug: "pharmacy-medical-delivery-guide",
    pillar: "industry-delivery-guides",
    title: "Pharmacy and medical delivery: compliance and speed",
    description: "Temperature, chain of custody, and SLA for pharmacy and medical.",
    links: {
      industrySlugs: ["pharmacy-medical"],
      serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "cosmetics-beauty-delivery-guide",
    pillar: "industry-delivery-guides",
    title: "Cosmetics and beauty delivery: D2C and retail",
    description: "Fragile handling and subscription delivery for beauty brands.",
    links: {
      industrySlugs: ["cosmetics"],
      serviceAreaSlugs: ["toronto"],
      deliveryPairs: [["cosmetics", "toronto"]],
      primaryCta: "merchant",
    },
  },
  {
    slug: "lab-sample-delivery-guide",
    pillar: "industry-delivery-guides",
    title: "Lab sample delivery: timing and reliability",
    description: "Pickup windows, same-day, and reporting for lab and clinical samples.",
    links: {
      industrySlugs: ["lab-sample-delivery"],
      serviceAreaSlugs: ["toronto", "kitchener-waterloo", "london"],
      primaryCta: "merchant",
    },
  },
  {
    slug: "chocolate-confectionery-delivery-guide",
    pillar: "industry-delivery-guides",
    title: "Chocolate and confectionery: local delivery that protects product",
    description: "Packaging, temperature, and same-day for chocolate and confectionery.",
    links: {
      industrySlugs: ["chocolate"],
      serviceAreaSlugs: ["toronto", "niagara"],
      primaryCta: "merchant",
    },
  },
];

/** Pillar label for UI (e.g. blog index filters). */
export const ARTICLE_PILLAR_LABELS: Record<ArticlePillar, string> = {
  "delivery-strategies-local-brands": "Delivery strategies for local brands",
  "courier-cost-optimization": "Courier cost optimization",
  "last-mile-insights": "Last-mile delivery insights",
  "industry-delivery-guides": "Industry delivery guides",
};

export function getArticleTopicBySlug(slug: string): ArticleTopic | null {
  return ARTICLE_TOPICS.find((t) => t.slug === slug) ?? null;
}

export function getArticleTopicsByPillar(pillar: ArticlePillar): ArticleTopic[] {
  return ARTICLE_TOPICS.filter((t) => t.pillar === pillar);
}
