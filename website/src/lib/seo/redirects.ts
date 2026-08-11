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
      source: `/${locale}/industry`,
      destination: `/${locale}/business#industries`,
      permanent: true,
      note: "Industries hub → merchants industries section",
    },
    {
      source: `/${locale}/quote`,
      destination: `/${locale}/sign-up?intent=quote&from=quote`,
      permanent: true,
      note: "Legacy /quote → business capacity form",
    },
    {
      source: `/${locale}/success-stories`,
      destination: `/${locale}/business`,
      permanent: true,
      note: "Success stories hub retired until permissioned stories exist",
    },
    {
      source: `/${locale}/success-stories/:slug`,
      destination: `/${locale}/business`,
      permanent: true,
      note: "Success story leaves retired until permissioned stories exist",
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

/** All website redirects — order preserved for documentation; Next.js resolves independently. */
export const WEBSITE_REDIRECTS: WebsiteRedirect[] = [
  ...platformSignInAliasRedirects(),
  ...legacyMarketRedirects(),
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
