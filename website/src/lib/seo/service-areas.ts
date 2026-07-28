import {
  DRAFT_SERVICE_AREA_MESSAGE_KEYS,
  DRAFT_SERVICE_AREA_SLUGS,
  type DraftServiceAreaSlug,
} from "./content/draft-expansions";

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
  ...DRAFT_SERVICE_AREA_SLUGS,
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
  ...(DRAFT_SERVICE_AREA_MESSAGE_KEYS as Record<DraftServiceAreaSlug, string>),
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

/** Playbook §4.5 — eight metros with established operational evidence. */
export const CORE_SERVICE_AREA_SLUGS = [
  "toronto",
  "mississauga",
  "brampton",
  "vaughan",
  "markham",
  "oakville",
  "hamilton",
  "kitchener-waterloo",
] as const;

export type CoreServiceAreaSlug = (typeof CORE_SERVICE_AREA_SLUGS)[number];

export function isCoreServiceArea(slug: string): slug is CoreServiceAreaSlug {
  return (CORE_SERVICE_AREA_SLUGS as readonly string[]).includes(slug);
}
