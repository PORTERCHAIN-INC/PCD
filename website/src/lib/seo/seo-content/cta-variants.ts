/**
 * CTA variant config for SEO content expansion.
 * Defines which CTA variants exist and their context.
 * Copy lives in messages (nicheLanding.*.cta, serviceAreaLanding.*.cta, etc.).
 */

import type { CTAVariantConfig } from "./types";
import { NICHE_SLUGS } from "../niche-landing";
import { SERVICE_AREA_SLUGS } from "../service-areas";
import { CAMPAIGN_SLUGS } from "../campaign-landing";
import { isDraftNicheSlug } from "../content/draft-expansions";

const DEFAULT_CTA: CTAVariantConfig = {
  variantKey: "default",
  context: "default",
  generationHints: {
    instruction: "Generic merchant CTA: talk to us, contact.",
  },
};

const INDUSTRY_CTA_VARIANTS: CTAVariantConfig[] = NICHE_SLUGS.filter(
  (slug) => !isDraftNicheSlug(slug)
).map((slug) => ({
  variantKey: `industry-${slug}`,
  context: "industry",
  entitySlug: slug,
  generationHints: {
    keywords: [slug.replace(/-/g, " ")],
    instruction: "Industry-specific CTA: primary = Talk to us, secondary = Contact.",
  },
}));

const SERVICE_AREA_CTA_VARIANTS: CTAVariantConfig[] = [
  DEFAULT_CTA,
  ...SERVICE_AREA_SLUGS.map((slug) => ({
    variantKey: `service-area-${slug}`,
    context: "service-area" as const,
    entitySlug: slug,
    generationHints: {
      keywords: [slug.replace(/-/g, " "), "delivery"],
      instruction: "Local CTA: ready for delivery in [area], talk to us.",
    },
  })),
];

const CAMPAIGN_CTA_VARIANTS: CTAVariantConfig[] = CAMPAIGN_SLUGS.map((slug) => ({
  variantKey: `campaign-${slug}`,
  context: "campaign" as const,
  entitySlug: slug,
  generationHints: {
    instruction: "Conversion-focused CTA for campaign landing.",
  },
}));

const CITY_INDUSTRY_CTA_TEMPLATE: CTAVariantConfig = {
  variantKey: "city-industry",
  context: "city-industry",
  generationHints: {
    instruction: "Combine city + industry (e.g. coffee delivery in Toronto — talk to us).",
  },
};

/** All CTA variant configs. */
export const CTA_VARIANT_CONFIGS: CTAVariantConfig[] = [
  DEFAULT_CTA,
  ...INDUSTRY_CTA_VARIANTS,
  ...SERVICE_AREA_CTA_VARIANTS.filter((v) => v.variantKey !== "default"),
  ...CAMPAIGN_CTA_VARIANTS,
  CITY_INDUSTRY_CTA_TEMPLATE,
];

export function getCTAVariantConfig(variantKey: string): CTAVariantConfig | null {
  return CTA_VARIANT_CONFIGS.find((c) => c.variantKey === variantKey) ?? null;
}

export function getCTAVariantConfigForEntity(
  context: CTAVariantConfig["context"],
  entitySlug?: string
): CTAVariantConfig | null {
  if (context === "default") return getCTAVariantConfig("default");
  if (context === "city-industry") return getCTAVariantConfig("city-industry");
  const found = CTA_VARIANT_CONFIGS.find(
    (c) => c.context === context && c.entitySlug === entitySlug
  );
  return found ?? null;
}
