/**
 * Service area (city/region) config for SEO content expansion.
 * Single source of truth for area slugs, message keys, regions, and generation hints.
 * Aligns with lib/service-areas.ts and messages.serviceAreaLanding.*
 */

import type { ServiceAreaConfig } from "./types";
import { SERVICE_AREA_SLUGS, SERVICE_AREA_MESSAGE_KEYS } from "../service-areas";
import type { ServiceAreaSlug } from "../service-areas";

/** Display label and region per slug. Areas with full content in messages use hasFullContent: true. */
const AREA_META: Partial<
  Record<ServiceAreaSlug, { label: string; region?: string; hasFullContent: boolean }>
> = {
  toronto: { label: "Toronto", region: "GTA", hasFullContent: true },
  mississauga: { label: "Mississauga", region: "Peel", hasFullContent: true },
  brampton: { label: "Brampton", region: "Peel", hasFullContent: true },
  vaughan: { label: "Vaughan", region: "York Region", hasFullContent: true },
  markham: { label: "Markham", region: "York Region", hasFullContent: true },
  oakville: { label: "Oakville", region: "Halton", hasFullContent: true },
  burlington: { label: "Burlington", region: "Halton", hasFullContent: true },
  oshawa: { label: "Oshawa", region: "Durham Region", hasFullContent: true },
  "kitchener-waterloo": {
    label: "Kitchener-Waterloo",
    region: "Region of Waterloo",
    hasFullContent: true,
  },
  london: { label: "London", region: "Southwestern Ontario", hasFullContent: true },
  "st-catharines": {
    label: "St. Catharines",
    region: "Niagara region",
    hasFullContent: true,
  },
  niagara: {
    label: "Niagara",
    region: "Niagara region",
    hasFullContent: true,
  },
  cambridge: {
    label: "Cambridge",
    region: "Region of Waterloo",
    hasFullContent: true,
  },
  guelph: { label: "Guelph", region: "Wellington County", hasFullContent: true },
  hamilton: {
    label: "Hamilton",
    region: "Golden Horseshoe",
    hasFullContent: true,
  },
  ajax: { label: "Ajax", region: "Durham Region", hasFullContent: true },
  pickering: { label: "Pickering", region: "Durham Region", hasFullContent: true },
};

/** Service area configs. Used for city pages and city-industry page generation. */
export const SERVICE_AREA_CONFIGS: ServiceAreaConfig[] = SERVICE_AREA_SLUGS.map((slug) => {
  const meta = AREA_META[slug];
  return {
    id: `service-area-${slug}`,
    slug,
    messageKey: SERVICE_AREA_MESSAGE_KEYS[slug],
    label: meta?.label ?? slug.replace(/-/g, " "),
    region: meta?.region,
    hasFullContent: meta?.hasFullContent ?? false,
    generationHints: meta?.hasFullContent
      ? { keywords: [meta.label, meta?.region].filter(Boolean) as string[] }
      : undefined,
  };
});

export function getServiceAreaConfig(slug: string): ServiceAreaConfig | null {
  const found = SERVICE_AREA_CONFIGS.find((c) => c.slug === slug);
  return found ?? null;
}

export function getServiceAreaConfigByMessageKey(messageKey: string): ServiceAreaConfig | null {
  const found = SERVICE_AREA_CONFIGS.find((c) => c.messageKey === messageKey);
  return found ?? null;
}
