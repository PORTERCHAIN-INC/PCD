/**
 * FAQ variant config for SEO content expansion.
 * Defines which FAQ variants exist and their context (default, industry, service-area, etc.).
 * Copy lives in messages (nicheLanding.*.faq, serviceAreaLanding.*.faq, campaignLanding.*.faq);
 * this registry is for validation, generation hints, and future city-industry pages.
 */

import type { FAQVariantConfig } from "./types";
import { NICHE_SLUGS } from "../niche-landing";
import { SERVICE_AREA_SLUGS } from "../service-areas";
import { CAMPAIGN_SLUGS } from "../campaign-landing";
import { isDraftNicheSlug } from "../content/draft-expansions";

/** Standard number of FAQ items per page (matches current message shape: q1/q2/q3, a1/a2/a3). */
const DEFAULT_FAQ_ITEM_COUNT = 3;

/** Default FAQ variant (e.g. serviceAreaLanding.default.faq). */
const DEFAULT_FAQ: FAQVariantConfig = {
  variantKey: "default",
  context: "default",
  itemCount: DEFAULT_FAQ_ITEM_COUNT,
  generationHints: {
    instruction: "General merchant delivery: coverage, speed, tracking.",
  },
};

/** Industry-specific FAQ variants (nicheLanding.<messageKey>.faq). */
const INDUSTRY_FAQ_VARIANTS: FAQVariantConfig[] = NICHE_SLUGS.filter(
  (slug) => !isDraftNicheSlug(slug)
).map((slug) => ({
  variantKey: `industry-${slug}`,
  context: "industry",
  entitySlug: slug,
  itemCount: DEFAULT_FAQ_ITEM_COUNT,
  generationHints: {
    keywords: [slug.replace(/-/g, " ")],
    instruction: "Industry-specific FAQs: capabilities, compliance, tracking.",
  },
}));

/** Service-area-specific FAQ variants (serviceAreaLanding.<messageKey>.faq or default). */
const SERVICE_AREA_FAQ_VARIANTS: FAQVariantConfig[] = [
  DEFAULT_FAQ,
  ...SERVICE_AREA_SLUGS.map((slug) => ({
    variantKey: `service-area-${slug}`,
    context: "service-area" as const,
    entitySlug: slug,
    itemCount: DEFAULT_FAQ_ITEM_COUNT,
    generationHints: {
      keywords: [slug.replace(/-/g, " "), "delivery", "coverage"],
      instruction: "Local delivery FAQs: coverage, time windows, tracking.",
    },
  })),
];

/** Campaign FAQ variants (campaignLanding.<messageKey>.faq). */
const CAMPAIGN_FAQ_VARIANTS: FAQVariantConfig[] = CAMPAIGN_SLUGS.map((slug) => ({
  variantKey: `campaign-${slug}`,
  context: "campaign" as const,
  entitySlug: slug,
  itemCount: DEFAULT_FAQ_ITEM_COUNT,
  generationHints: {
    instruction: "Conversion-focused FAQs for campaign landing.",
  },
}));

/** City-industry (future): one FAQ block per (serviceArea, industry) pair. */
const CITY_INDUSTRY_FAQ_TEMPLATE: FAQVariantConfig = {
  variantKey: "city-industry",
  context: "city-industry",
  itemCount: DEFAULT_FAQ_ITEM_COUNT,
  generationHints: {
    instruction:
      "Combine local delivery (city) with industry-specific angles (e.g. coffee delivery in Toronto).",
  },
};

/** All FAQ variant configs. Use variantKey to look up or generate copy. */
export const FAQ_VARIANT_CONFIGS: FAQVariantConfig[] = [
  DEFAULT_FAQ,
  ...INDUSTRY_FAQ_VARIANTS,
  ...SERVICE_AREA_FAQ_VARIANTS.filter((v) => v.variantKey !== "default"),
  ...CAMPAIGN_FAQ_VARIANTS,
  CITY_INDUSTRY_FAQ_TEMPLATE,
];

export function getFAQVariantConfig(variantKey: string): FAQVariantConfig | null {
  return FAQ_VARIANT_CONFIGS.find((c) => c.variantKey === variantKey) ?? null;
}

export function getFAQVariantConfigForEntity(
  context: FAQVariantConfig["context"],
  entitySlug?: string
): FAQVariantConfig | null {
  if (context === "default") return getFAQVariantConfig("default");
  if (context === "city-industry") return getFAQVariantConfig("city-industry");
  const found = FAQ_VARIANT_CONFIGS.find(
    (c) => c.context === context && c.entitySlug === entitySlug
  );
  return found ?? null;
}
