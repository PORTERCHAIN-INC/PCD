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

function guideConsolidationRedirects(): WebsiteRedirect[] {
  return LOCALES.map((locale) => ({
    source: `/${locale}/guides/how-porterchain-works`,
    destination: `/${locale}/how-porterchain-works`,
    permanent: true,
    note: "Canonical how-it-works route",
  }));
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

function constructionShortUrlRedirects(): WebsiteRedirect[] {
  return LOCALES.map((locale) => ({
    source: `/${locale}/solutions/construction`,
    destination: `/${locale}/construction`,
    permanent: true,
    note: "Construction solutions hub short URL",
  }));
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
      destination: `/${locale}/success-stories`,
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
export const WEBSITE_REDIRECTS: WebsiteRedirect[] = [
  ...platformSignInAliasRedirects(),
  ...legacyMarketRedirects(),
  ...legacySiteRedirects(),
  ...corporateOverviewRedirects(),
  ...guideConsolidationRedirects(),
  ...vehicleSlugRedirects(),
  ...educationHubRedirects(),
  ...constructionShortUrlRedirects(),
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
