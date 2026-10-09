/**
 * Internal linking between industry, service area, and city-industry SEO pages.
 */
import type { Locale } from "@/i18n/routing";
import { solutionVerticalPath, type SolutionVerticalSlug } from "@/lib/solutions-verticals";
import {
  cityIndustrySeo,
  faqSlug,
  industrySlug,
  localePath,
  platform,
  serviceAreaSlug,
} from "./routes";
import { getFaqClusterBySlug } from "./content/faq-clusters";
import {
  isValidCitySeoSlug,
  CITY_SEO_TO_SERVICE_AREA,
  INDUSTRY_SEO_TO_NICHE,
  type CitySeoSlug,
  type IndustrySeoSlug,
} from "./city-industry-seo";
import { getNicheMessageKey } from "./niche-landing";
import { VEHICLE_CITY_SEO_SLUGS, type VehicleCitySeoSlug } from "./city-segment-seo";

const CITY_SEO_SLUGS_FOR_LINKS: CitySeoSlug[] = [
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "oakville",
  "oshawa",
  "kitchener",
  "hamilton",
  "london",
  "st-catharines",
  "niagara",
];

const SERVICE_AREA_TO_CITY_SEO: Record<string, CitySeoSlug> = {
  toronto: "toronto",
  mississauga: "mississauga",
  brampton: "brampton",
  vaughan: "vaughan",
  oakville: "oakville",
  oshawa: "oshawa",
  "kitchener-waterloo": "kitchener",
  hamilton: "hamilton",
  london: "london",
  "st-catharines": "st-catharines",
  niagara: "niagara",
};

const NICHE_TO_INDUSTRY_SEO: Record<string, string> = {
  "construction-materials": "construction-materials-delivery",
  "electrical-distribution": "electrical-delivery",
  "plumbing-supply": "plumbing-supply-delivery",
  "coffee-roasters": "coffee-roaster-delivery",
  "pharmacy-medical": "pharmacy-delivery",
  cosmetics: "cosmetics-delivery",
  chocolate: "chocolate-delivery",
  "lab-sample-delivery": "lab-sample-delivery",
  ecommerce: "ecommerce-delivery",
};

export const INDUSTRY_SLUGS_FOR_CITY_LINKS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
  "ecommerce",
  "coffee-roasters",
  "pharmacy-medical",
  "cosmetics",
  "chocolate",
  "lab-sample-delivery",
] as const;

export const ANCHOR_PHRASE_BY_INDUSTRY_KEY: Record<string, string> = {
  constructionMaterials: "Construction materials delivery",
  electricalDistribution: "Electrical distributor delivery",
  plumbingSupply: "Plumbing supply delivery",
  coffeeRoasters: "Coffee roaster delivery",
  pharmacyMedical: "Pharmacy courier",
  cosmetics: "Cosmetics delivery",
  chocolate: "Chocolate delivery",
  labSampleDelivery: "Lab sample delivery",
  ecommerce: "E-commerce delivery",
};

/** Intent-cluster FAQ hubs (Wave 9 user-intent linking). */
export const INTENT_HUB_FAQ_SLUGS = [
  "same-day-retail-distribution",
  "fleet-overflow-wholesale-delivery",
] as const;

/** Max curated next links on SEO detail pages (playbook §7). */
export const MAX_DETAIL_PAGE_LINKS = 5;

function curateLinks<T>(links: readonly T[], max = MAX_DETAIL_PAGE_LINKS): T[] {
  return links.slice(0, max);
}

/** Reverse map: niche slug → solutions vertical for internal links. */
const NICHE_TO_SOLUTION_VERTICAL: Partial<Record<string, SolutionVerticalSlug>> = {
  "construction-materials": "construction",
  "electrical-distribution": "construction",
  "plumbing-supply": "construction",
  "pharmacy-medical": "medical",
  "coffee-roasters": "food-beverage",
  ecommerce: "wholesale",
};

const SOLUTION_VERTICAL_LABELS: Record<SolutionVerticalSlug, string> = {
  wholesale: "Wholesale distribution solutions",
  medical: "Medical & healthcare solutions",
  "food-beverage": "Food & beverage solutions",
  construction: "Construction supply solutions",
  "3pl": "3PL & warehouse solutions",
  "fleet-overflow": "Fleet overflow solutions",
};

export const INDUSTRY_PAGE_LABELS: Record<string, string> = {
  "construction-materials": "Construction materials",
  "electrical-distribution": "Electrical distribution",
  "plumbing-supply": "Plumbing supply",
  "coffee-roasters": "Coffee roasters",
  "pharmacy-medical": "Pharmacy & medical",
  cosmetics: "Cosmetics & beauty",
  chocolate: "Chocolate & confectionery",
  "lab-sample-delivery": "Lab sample delivery",
  ecommerce: "E-commerce",
  "hvac-mechanical": "HVAC & mechanical (draft)",
  "automotive-parts": "Automotive parts (draft)",
  manufacturing: "Manufacturing (draft)",
  "retail-replenishment": "Retail replenishment (draft)",
  "food-distribution": "Food distribution (draft)",
};

const LOCAL_DELIVERY_CITY_LABELS: Record<CitySeoSlug, string> = {
  toronto: "Toronto",
  mississauga: "Mississauga",
  brampton: "Brampton",
  vaughan: "Vaughan",
  oakville: "Oakville",
  oshawa: "Oshawa",
  kitchener: "Kitchener",
  hamilton: "Hamilton",
  london: "London",
  "st-catharines": "St. Catharines",
  niagara: "Niagara",
};

type MessagesWithLabels = {
  cityIndustryDelivery?: {
    industryLabels?: Record<string, string>;
    areaLabels?: Record<string, string>;
  };
};

export function buildCityDeliveryLinksForIndustryPage(
  locale: Locale,
  nicheSlug: string,
  messages: MessagesWithLabels
): { href: string; label: string }[] {
  const industryKey = getNicheMessageKey(nicheSlug);
  if (!industryKey) return [];
  const industrySeoSlug = NICHE_TO_INDUSTRY_SEO[nicheSlug];
  if (!industrySeoSlug) return [];
  const anchorPhrase = ANCHOR_PHRASE_BY_INDUSTRY_KEY[industryKey] ?? nicheSlug;
  const links: { href: string; label: string }[] = [];
  for (const citySeo of CITY_SEO_SLUGS_FOR_LINKS) {
    const areaKey = CITY_SEO_TO_SERVICE_AREA[citySeo];
    const cityLabel =
      messages.cityIndustryDelivery?.areaLabels?.[areaKey.replace(/-/g, "")] ??
      LOCAL_DELIVERY_CITY_LABELS[citySeo];
    links.push({
      href: cityIndustrySeo(locale, citySeo, industrySeoSlug),
      label: `${anchorPhrase} ${cityLabel}`,
    });
  }
  return curateLinks(links);
}

export function buildLocalDeliveryCityLinks(locale: Locale): { href: string; label: string }[] {
  return curateLinks(
    CITY_SEO_SLUGS_FOR_LINKS.map((citySeo) => ({
      href: serviceAreaSlug(locale, CITY_SEO_TO_SERVICE_AREA[citySeo]),
      label: `Local delivery ${LOCAL_DELIVERY_CITY_LABELS[citySeo]}`,
    }))
  );
}

export function buildVehicleLinksForCityPage(
  locale: Locale,
  citySeo: string
): { href: string; label: string }[] {
  if (!isValidCitySeoSlug(citySeo)) return [];
  const cityLabel = LOCAL_DELIVERY_CITY_LABELS[citySeo];
  const labels: Record<VehicleCitySeoSlug, string> = {
    "sedan-delivery": "Sedan",
    "suv-delivery": "SUV",
    "trade-van-delivery": "Trade van",
    "pickup-truck-delivery": "Pickup truck",
    "cargo-van-delivery": "Cargo van",
    "box-truck-delivery": "Box truck",
  };
  return curateLinks(
    VEHICLE_CITY_SEO_SLUGS.map((segment) => ({
      href: cityIndustrySeo(locale, citySeo, segment),
      label: `${labels[segment]} delivery ${cityLabel}`,
    })),
    4
  );
}

export function buildIndustryPageLinksForCityPage(
  locale: Locale
): { href: string; label: string }[] {
  return curateLinks(
    INDUSTRY_SLUGS_FOR_CITY_LINKS.map((slug) => ({
      href: industrySlug(locale, slug),
      label: INDUSTRY_PAGE_LABELS[slug] ?? slug.replace(/-/g, " "),
    }))
  );
}

export function buildIndustryDeliveryLinksForCityPage(
  locale: Locale,
  serviceAreaSlugValue: string,
  messages: MessagesWithLabels
): { href: string; label: string }[] {
  const citySeo = SERVICE_AREA_TO_CITY_SEO[serviceAreaSlugValue];
  if (!citySeo) return [];
  const cityLabel = LOCAL_DELIVERY_CITY_LABELS[citySeo];
  return curateLinks(
    INDUSTRY_SLUGS_FOR_CITY_LINKS.flatMap((nicheSlug) => {
      const industryKey = getNicheMessageKey(nicheSlug);
      const industrySeoSlug = NICHE_TO_INDUSTRY_SEO[nicheSlug];
      if (!industryKey || !industrySeoSlug) return [];
      const anchorPhrase = ANCHOR_PHRASE_BY_INDUSTRY_KEY[industryKey];
      return [
        {
          href: cityIndustrySeo(locale, citySeo, industrySeoSlug),
          label: `${anchorPhrase} ${cityLabel}`,
        },
      ];
    })
  );
}

/** Mandatory Lane B bridge links: platform, solutions vertical (when mapped), parent industry. */
export function buildProductLinksForNiche(
  locale: Locale,
  nicheSlug: string,
  from: string
): { href: string; label: string }[] {
  const links: { href: string; label: string }[] = [
    {
      href: platform(locale, { from }),
      label: "How Porterchain operates",
    },
  ];

  const vertical = NICHE_TO_SOLUTION_VERTICAL[nicheSlug];
  if (vertical) {
    links.push({
      href: `${localePath(locale, solutionVerticalPath(vertical).replace(/^\//, ""))}?from=${encodeURIComponent(from)}`,
      label: SOLUTION_VERTICAL_LABELS[vertical],
    });
  }

  if (INDUSTRY_PAGE_LABELS[nicheSlug]) {
    links.push({
      href: industrySlug(locale, nicheSlug),
      label: `${INDUSTRY_PAGE_LABELS[nicheSlug]} overview`,
    });
  }

  return links;
}

export function buildProductLinksForIndustrySeoSlug(
  locale: Locale,
  industrySeoSlug: string,
  from: string
): { href: string; label: string }[] {
  const nicheSlug = INDUSTRY_SEO_TO_NICHE[industrySeoSlug as IndustrySeoSlug];
  if (!nicheSlug) return buildProductLinksForNiche(locale, industrySeoSlug, from);
  return buildProductLinksForNiche(locale, nicheSlug, from);
}

/** Curated links to intent FAQ hubs (same-day retail, fleet overflow). */
export function buildIntentHubLinks(
  locale: Locale,
  from?: string,
  titleBySlug?: Partial<Record<(typeof INTENT_HUB_FAQ_SLUGS)[number], string>>
): { href: string; label: string }[] {
  return INTENT_HUB_FAQ_SLUGS.map((slug) => {
    const cluster = getFaqClusterBySlug(slug);
    const label = titleBySlug?.[slug] ?? cluster?.title ?? slug.replace(/-/g, " ");
    const baseHref = faqSlug(locale, slug);
    const href = from ? `${baseHref}?from=${encodeURIComponent(from)}` : baseHref;
    return { href, label };
  });
}

export function buildInternalLinksForArticle(
  locale: Locale,
  options?: { industrySlugs?: string[]; maxLinks?: number }
): { href: string; label: string }[] {
  const industrySlugs = options?.industrySlugs ?? [...INDUSTRY_SLUGS_FOR_CITY_LINKS];
  const max = options?.maxLinks ?? 12;
  const out: { href: string; label: string }[] = [];
  for (const slug of industrySlugs) {
    out.push({
      href: industrySlug(locale, slug),
      label: INDUSTRY_PAGE_LABELS[slug] ?? slug,
    });
  }
  for (const citySeo of CITY_SEO_SLUGS_FOR_LINKS) {
    if (!isValidCitySeoSlug(citySeo)) continue;
    out.push({
      href: serviceAreaSlug(locale, CITY_SEO_TO_SERVICE_AREA[citySeo]),
      label: `Local delivery ${LOCAL_DELIVERY_CITY_LABELS[citySeo]}`,
    });
  }
  return out.slice(0, max);
}

// re-export for content modules
export { INDUSTRY_SEO_TO_NICHE };
