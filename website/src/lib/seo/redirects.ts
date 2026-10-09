import { MERGED_DELIVERY_VERTICALS } from "@/lib/seo/delivery-programmatic";
/**
 * Central redirect registry for PorterChain website.
 * Consumed by next.config.ts — single source of truth for historical slugs.
 */

export type WebsiteRedirect = {
  source: string;
  destination: string;
  /** true = 308/301 permanent; false = 307/302 temporary */
  permanent: boolean;
  note?: string;
};

const LOCALES = ["en", "fr"] as const;

const removedCorporatePaths = ["overview"] as const;

/**
 * Paths from the 2025–2026 sites (/ca/en/*, locale-less PC/PORTERCHAIN apps) that Search
 * Console still knows. Sources are locale-prefixed because url-policy.ts strips /ca/* and adds
 * /en before matching. Destinations are live, indexable pages (url-policy test enforces it).
 */
function legacySiteRedirects(): WebsiteRedirect[] {
  const map: Array<[string, string]> = [
    ["about", "company"],
    ["services", "solutions"],
    ["industries", "solutions"],
    ["industries/:slug", "industry/:slug"],
    ["for-business", "business"],
    ["driver-partner", "vehicle-partner"],
    ["driver-partner-terms", "terms"],
    ["api-integrations", "integrations"],
    ["standards", "trust"],
    ["support", "contact"],
    ["report-issue", "contact"],
    ["get-started", "sign-up"],
    ["how-it-works", "how-porterchain-works"],
    ["product", "platform"],
    ["product/routing-dispatch", "capabilities/ai-dispatch"],
    ["product/merchant-setup", "how-porterchain-works"],
    ["status", "trust"],
    ["docs", "developers"],
    ["merchant", "business"],
    ["merchant-onboarding", "business"],
    ["merchant-workflow", "how-porterchain-works"],
    ["knowledge", "guides"],
    ["resources", "blog"],
    ["resources/category/:slug", "blog/category/:slug"],
    ["resources/:slug", "blog/:slug"],
    ["general-guidelines", "terms"],
    ["zero-tolerance-policy", "terms"],
    ["dashboard", "login"],
    // Blog slugs Search Console knows that have no surviving content (planned CMS posts and
    // 2026 /resources articles) → closest restored post or hub. Restored posts live in
    // website/content/blog and are NOT listed here.
    ["blog/bloglist", "blog"],
    ["blog/gta-commercial-logistics-guide", "guides"],
    ["blog/proof-of-delivery-commercial-shipments", "blog/audit-ready-proof-of-delivery"],
    ["blog/same-day-vs-scheduled-freight-gta", "blog/same-day-b2b-delivery-toronto"],
    ["blog/cosmetics-fulfillment", "industry/cosmetics"],
    ["blog/courier-pricing-breakdown", "delivery-cost-calculator"],
    ["blog/delivery-strategies-local-brands", "blog/retail-last-mile-visibility"],
    ["blog/logistics-for-coffee-roasters", "blog/coffee-supply-chain-freshness"],
    ["blog/pharmacy-delivery-logistics", "blog/pharmacy-same-day-courier-gta"],
    ["blog/route-optimization-insights", "blog/route-optimization-empty-miles"],
    ["blog/scaling-local-delivery", "blog/same-day-delivery-at-scale"],
  ];
  return LOCALES.flatMap((locale) =>
    map.map(([from, to]) => ({
      source: `/${locale}/${from}`,
      destination: `/${locale}/${to}`,
      permanent: true,
      note: "Legacy 2025–2026 site path (Search Console)",
    }))
  );
}

function legacyMarketRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) => [
    {
      source: `/ca/${locale === "en" ? "en" : "fr-ca"}/:path*`,
      destination: `/${locale}/:path*`,
      permanent: true,
      note: "Legacy /ca/en market prefix",
    },
    {
      source: `/ca/${locale === "en" ? "en" : "fr-ca"}`,
      destination: `/${locale}`,
      permanent: true,
      note: "Legacy /ca/en root",
    },
  ]);
}

function corporateOverviewRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) =>
    removedCorporatePaths.map((segment) => ({
      source: `/${locale}/${segment}`,
      destination: `/${locale}/business`,
      permanent: true,
      note: "Retired corporate overview → business",
    }))
  );
}

function vehicleSlugRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) => [
    {
      source: `/${locale}/van-delivery`,
      destination: `/${locale}/trade-van-delivery`,
      permanent: true,
      note: "Renamed vehicle segment",
    },
    {
      source: `/${locale}/medium-truck`,
      destination: `/${locale}/box-truck-delivery`,
      permanent: true,
      note: "Renamed vehicle segment",
    },
    {
      source: `/${locale}/:city/van-delivery`,
      destination: `/${locale}/:city/trade-van-delivery`,
      permanent: true,
      note: "City vehicle slug rename",
    },
    {
      source: `/${locale}/:city/medium-truck`,
      destination: `/${locale}/:city/box-truck-delivery`,
      permanent: true,
      note: "City vehicle slug rename",
    },
  ]);
}

function educationHubRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) =>
    (["onboarding-education", "integrations-education"] as const).map((path) => ({
      source: `/${locale}/${path}`,
      destination: `/${locale}/faq`,
      permanent: true,
      note: "Education hubs consolidated under FAQ index",
    }))
  );
}

/** Vanity hub labels → stable money URLs (single canonical). */
function hubVanityRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) => [
    {
      source: `/${locale}/merchants`,
      destination: `/${locale}/business`,
      permanent: true,
      note: "Merchants vanity → /business",
    },
    {
      source: `/${locale}/drivers`,
      destination: `/${locale}/vehicle-partner`,
      permanent: true,
      note: "Drivers vanity → /vehicle-partner",
    },
  ]);
}

/** Retired marketing hubs — content lives on /business (+ welcome home signals). */
function retiredMarketingHubRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) => [
    {
      source: `/${locale}/pricing`,
      destination: `/${locale}/business#pricing`,
      permanent: true,
      note: "Pricing hub → merchants billing section",
    },
    {
      source: `/${locale}/customers`,
      destination: `/${locale}/delivery`,
      permanent: true,
      note: "Customers orphan hub → permissioned success stories",
    },
    {
      source: `/${locale}/drive`,
      destination: `/${locale}/vehicle-partner`,
      permanent: true,
      note: "Legacy /drive → vehicle partner",
    },
    {
      source: `/${locale}/suv-delivery`,
      destination: `/${locale}/sedan-delivery`,
      permanent: true,
      note: "SUV segment folded into sedan delivery",
    },
    {
      source: `/${locale}/industry`,
      destination: `/${locale}/business#industries`,
      permanent: true,
      note: "Industries hub → merchants industries section",
    },
    {
      source: `/${locale}/quote`,
      destination: `/${locale}/sign-up?intent=quote`,
      permanent: true,
      note: "Legacy /quote → business capacity form",
    },
  ]);
}

function platformSignInAliasRedirects(): WebsiteRedirect[] {
  return [
    {
      source: "/sign-in",
      destination: "/login",
      permanent: true,
      note: "Portal deep-links may say /sign-in; Platform login is /login",
    },
    ...LOCALES.map((locale) => ({
      source: `/${locale}/sign-in`,
      destination: `/${locale}/login`,
      permanent: true,
      note: "Locale alias for Platform login",
    })),
  ];
}

/**
 * All website redirects. Applied by middleware via url-policy.ts (resolveUrlPolicy), which
 * collapses chains into a single 301 — they are deliberately NOT returned from next.config
 * redirects(), because those run before middleware and produced multi-hop chains.
 */

/**
 * Footer consolidation (Oct 2026): thin or duplicate pages merged into the page that helps the
 * visitor price, book, trust us or find what they came for. One 301 each (url-policy collapses
 * any older registry chain that pointed at these). Evidence: tmp/website-footer/keep-remove.md.
 */
function footerConsolidationRedirects(): WebsiteRedirect[] {
  const map: Array<[string, string]> = [
    // ~220-word capability stubs → the guide that covers the same topic, else /platform.
    ["capabilities/multi-location-routing", "guides/multi-location-capacity-gta"],
    ["capabilities/inventory-transfers", "guides/inventory-transfers-between-locations"],
    ["capabilities/exception-recovery", "guides/delivery-failure-modes-and-recovery"],
    ["capabilities/:slug", "platform"],
    ["capabilities", "platform"],
    // Integration explainer stubs (~250 words each) → the integrations / developer hubs.
    ["integrations-education/api-order-ingestion", "developers"],
    ["integrations-education/webhooks-delivery-events", "developers"],
    ["integrations-education/:slug", "integrations"],
    // /solutions duplicated the /delivery industry hubs.
    ["solutions/wholesale", "delivery/warehouses"],
    ["solutions/medical", "delivery/pharmacy"],
    ["solutions/3pl", "delivery/warehouses"],
    ["solutions/fleet-overflow", "business"],
    ["solutions/construction", "delivery/construction"],
    ...[
      "furniture",
      "furniture-delivery",
      "furniture-appliance-delivery",
      "furniture-and-appliance-delivery",
      "appliance-delivery",
    ].map((slug): [string, string] => [`solutions/${slug}`, "delivery/furniture"]),
    ["solutions/:slug", "delivery"],
    ["solutions", "delivery"],
    ["construction", "delivery/construction"],
    // Same sections as /platform ("From capacity request to proof of delivery" …).
    ["how-porterchain-works", "platform"],
    // Thin hubs (Oct 2026 QA): a 5-link city list, and case studies with unverifiable quotes/stats.
    ["local-delivery", "service-areas"],
    ["success-stories/construction-distributor-jobsite-delivery", "delivery/construction"],
    ["success-stories/plumbing-supply-counter-to-jobsite", "delivery/construction"],
    ["success-stories/electrical-wholesaler-overflow-capacity", "delivery/construction"],
    ["success-stories/pharmacy-patient-delivery", "delivery/pharmacy"],
    ["success-stories/3pl-warehouse-outbound-peel", "delivery/warehouses"],
    ["success-stories/coffee-roaster-wholesale-delivery", "delivery/warehouses"],
    ["success-stories/beauty-brand-d2c-fulfillment", "delivery/shopify-merchants"],
    ["success-stories/:slug", "delivery"],
    ["success-stories", "delivery"],
    ["guides/how-porterchain-works", "platform"],
  ];
  return LOCALES.flatMap((locale) =>
    map.map(([from, to]) => ({
      source: `/${locale}/${from}`,
      destination: `/${locale}/${to}`,
      permanent: true,
      note: "Footer consolidation (Oct 2026)",
    }))
  );
}

/** Industry merges (Oct 2026): weak or overlapping industry hubs fold into the surviving hub. */
function industryMergeRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) =>
    Object.entries(MERGED_DELIVERY_VERTICALS).flatMap(([from, to]) => [
      {
        source: `/${locale}/delivery/${from}`,
        destination: `/${locale}/delivery/${to}`,
        permanent: true,
        note: "Industry merge (Oct 2026)",
      },
      {
        source: `/${locale}/delivery/${from}/:area`,
        destination: `/${locale}/delivery/${to}/:area`,
        permanent: true,
        note: "Industry merge (Oct 2026)",
      },
    ])
  );
}

/** FAQ consolidation (Oct 2026): every /faq/{cluster} page merged into /faq or its topic page. */
export const FAQ_CLUSTER_DESTINATION: Record<string, string> = {
  "construction-delivery": "delivery/construction",
  "electrical-distributor-delivery": "delivery/construction",
  "plumbing-supply-delivery": "delivery/construction",
  "delivery-pricing": "delivery-cost-calculator",
  "how-much-does-local-delivery-cost-toronto": "delivery-cost-calculator",
  onboarding: "faq",
  "csv-uploads": "developers",
  "api-integrations": "developers",
  "local-service-areas": "service-areas",
  "pharmacy-delivery": "delivery/pharmacy",
  "how-pharmacy-courier-delivery-works-gta": "delivery/pharmacy",
  "coffee-roaster-delivery": "delivery/warehouses",
  "how-to-set-up-recurring-deliveries-coffee-roaster": "delivery/warehouses",
  "cosmetics-delivery": "delivery/shopify-merchants",
  "same-day-delivery": "delivery",
  "same-day-retail-distribution": "delivery",
  "how-to-onboard-merchant-csv-upload": "developers",
  "what-vehicle-right-for-parcel-volume": "vehicles",
  "fleet-overflow-wholesale-delivery": "delivery/warehouses",
};

function faqConsolidationRedirects(): WebsiteRedirect[] {
  return LOCALES.flatMap((locale) => [
    ...Object.entries(FAQ_CLUSTER_DESTINATION).map(([slug, to]) => ({
      source: `/${locale}/faq/${slug}`,
      destination: `/${locale}/${to}`,
      permanent: true,
      note: "FAQ consolidation (Oct 2026)",
    })),
    {
      source: `/${locale}/faq/:slug`,
      destination: `/${locale}/faq`,
      permanent: true,
      note: "FAQ consolidation (Oct 2026)",
    },
  ]);
}

export const WEBSITE_REDIRECTS: WebsiteRedirect[] = [
  ...faqConsolidationRedirects(),
  ...industryMergeRedirects(),
  ...footerConsolidationRedirects(),
  ...platformSignInAliasRedirects(),
  ...legacyMarketRedirects(),
  ...legacySiteRedirects(),
  ...corporateOverviewRedirects(),
  ...vehicleSlugRedirects(),
  ...educationHubRedirects(),
  ...hubVanityRedirects(),
  ...retiredMarketingHubRedirects(),
];

/** Shape for Next.js redirects() config. */
export function toNextRedirects(): Array<{
  source: string;
  destination: string;
  permanent: boolean;
}> {
  return WEBSITE_REDIRECTS.map(({ source, destination, permanent }) => ({
    source,
    destination,
    permanent,
  }));
}
