/**
 * Reusable service area page framework.
 * Valid slugs and mapping to message keys. SEO-friendly static params.
 */

export const SERVICE_AREA_SLUGS = [
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "markham",
  "oakville",
  "burlington",
  "oshawa",
  "kitchener-waterloo",
  "london",
  "st-catharines",
  "niagara",
  "cambridge",
  "guelph",
  "hamilton",
  "ajax",
  "pickering",
] as const;

export type ServiceAreaSlug = (typeof SERVICE_AREA_SLUGS)[number];

/** Message key per slug for serviceAreaLanding.* in messages. CamelCase. */
export const SERVICE_AREA_MESSAGE_KEYS: Record<ServiceAreaSlug, string> = {
  toronto: "toronto",
  mississauga: "mississauga",
  brampton: "brampton",
  vaughan: "vaughan",
  markham: "markham",
  oakville: "oakville",
  burlington: "burlington",
  oshawa: "oshawa",
  "kitchener-waterloo": "kitchenerWaterloo",
  london: "london",
  "st-catharines": "stCatharines",
  niagara: "niagara",
  cambridge: "cambridge",
  guelph: "guelph",
  hamilton: "hamilton",
  ajax: "ajax",
  pickering: "pickering",
};

export function getServiceAreaMessageKey(slug: string): string | null {
  if (SERVICE_AREA_SLUGS.includes(slug as ServiceAreaSlug)) {
    return SERVICE_AREA_MESSAGE_KEYS[slug as ServiceAreaSlug];
  }
  return null;
}

export function isValidServiceAreaSlug(slug: string): slug is ServiceAreaSlug {
  return SERVICE_AREA_SLUGS.includes(slug as ServiceAreaSlug);
}
