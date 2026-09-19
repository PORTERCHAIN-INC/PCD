/**
 * City + industry SEO URL slugs and mapping.
 * Powers routes like /toronto/construction-materials-delivery.
 */

/** City segment in URL (e.g. toronto, kitchener). May differ from service-area slug (e.g. kitchener → kitchener-waterloo). */
export const CITY_SEO_SLUGS = [
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
] as const;

export type CitySeoSlug = (typeof CITY_SEO_SLUGS)[number];

/** Industry segment in URL. Construction trades listed first. */
export const INDUSTRY_SEO_SLUGS = [
  "construction-materials-delivery",
  "electrical-delivery",
  "plumbing-supply-delivery",
  "coffee-roaster-delivery",
  "pharmacy-delivery",
  "cosmetics-delivery",
  "chocolate-delivery",
  "lab-sample-delivery",
  "ecommerce-delivery",
] as const;

export type IndustrySeoSlug = (typeof INDUSTRY_SEO_SLUGS)[number];

/** URL city slug → service area slug (for getCityIndustryContent). */
export const CITY_SEO_TO_SERVICE_AREA: Record<CitySeoSlug, string> = {
  toronto: "toronto",
  mississauga: "mississauga",
  brampton: "brampton",
  vaughan: "vaughan",
  oakville: "oakville",
  oshawa: "oshawa",
  kitchener: "kitchener-waterloo",
  hamilton: "hamilton",
  london: "london",
  "st-catharines": "st-catharines",
  niagara: "niagara",
};

/** URL industry slug → niche slug (for getCityIndustryContent). */
export const INDUSTRY_SEO_TO_NICHE: Record<IndustrySeoSlug, string> = {
  "construction-materials-delivery": "construction-materials",
  "electrical-delivery": "electrical-distribution",
  "plumbing-supply-delivery": "plumbing-supply",
  "coffee-roaster-delivery": "coffee-roasters",
  "pharmacy-delivery": "pharmacy-medical",
  "cosmetics-delivery": "cosmetics",
  "chocolate-delivery": "chocolate",
  "lab-sample-delivery": "lab-sample-delivery",
  "ecommerce-delivery": "ecommerce",
};

export function isValidCitySeoSlug(s: string): s is CitySeoSlug {
  return (CITY_SEO_SLUGS as readonly string[]).includes(s);
}

export function isValidIndustrySeoSlug(s: string): s is IndustrySeoSlug {
  return (INDUSTRY_SEO_SLUGS as readonly string[]).includes(s);
}

/** Resolve URL (city, industrySlug) to (nicheSlug, serviceAreaSlug) for getCityIndustryContent. Returns null if invalid. */
export function resolveCityIndustrySeo(
  cityUrlSlug: string,
  industryUrlSlug: string
): { nicheSlug: string; serviceAreaSlug: string } | null {
  if (!isValidCitySeoSlug(cityUrlSlug) || !isValidIndustrySeoSlug(industryUrlSlug)) return null;
  return {
    nicheSlug: INDUSTRY_SEO_TO_NICHE[industryUrlSlug],
    serviceAreaSlug: CITY_SEO_TO_SERVICE_AREA[cityUrlSlug],
  };
}

/** All valid (cityUrlSlug, industryUrlSlug) pairs for static params. */
export function getCityIndustrySeoPairs(): { city: CitySeoSlug; industrySlug: IndustrySeoSlug }[] {
  const pairs: { city: CitySeoSlug; industrySlug: IndustrySeoSlug }[] = [];
  for (const city of CITY_SEO_SLUGS) {
    for (const industrySlug of INDUSTRY_SEO_SLUGS) {
      pairs.push({ city, industrySlug });
    }
  }
  return pairs;
}
