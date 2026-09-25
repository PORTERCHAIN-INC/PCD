/**
 * Onboarding messaging variant config for SEO content expansion.
 * Defines which onboarding block variants exist (title, description, 3 steps).
 * Copy lives in messages (nicheLanding.*.onboarding, serviceAreaLanding.*.onboarding, etc.).
 */

import type { OnboardingVariantConfig } from "./types";
import { NICHE_SLUGS } from "../niche-landing";
import { SERVICE_AREA_SLUGS } from "../service-areas";
import { CAMPAIGN_SLUGS } from "../campaign-landing";
import { isDraftNicheSlug } from "../content/draft-expansions";

const DEFAULT_ONBOARDING_STEP_COUNT = 3;

const DEFAULT_ONBOARDING: OnboardingVariantConfig = {
  variantKey: "default",
  context: "default",
  stepCount: DEFAULT_ONBOARDING_STEP_COUNT,
  generationHints: {
    instruction:
      "Three steps: Connect (volume/zones), We deliver (pickup + tracking), You stay in control (ETAs, reporting).",
  },
};

const INDUSTRY_ONBOARDING_VARIANTS: OnboardingVariantConfig[] = NICHE_SLUGS.filter(
  (slug) => !isDraftNicheSlug(slug)
).map((slug) => ({
  variantKey: `industry-${slug}`,
  context: "industry",
  entitySlug: slug,
  stepCount: DEFAULT_ONBOARDING_STEP_COUNT,
  generationHints: {
    keywords: [slug.replace(/-/g, " ")],
    instruction: "Same 3-step structure, industry-appropriate wording.",
  },
}));

const SERVICE_AREA_ONBOARDING_VARIANTS: OnboardingVariantConfig[] = [
  DEFAULT_ONBOARDING,
  ...SERVICE_AREA_SLUGS.map((slug) => ({
    variantKey: `service-area-${slug}`,
    context: "service-area" as const,
    entitySlug: slug,
    stepCount: DEFAULT_ONBOARDING_STEP_COUNT,
    generationHints: {
      keywords: [slug.replace(/-/g, " "), "local", "capacity"],
      instruction: "Onboarding for [area] merchants: connect, we deliver, you stay in control.",
    },
  })),
];

const CAMPAIGN_ONBOARDING_VARIANTS: OnboardingVariantConfig[] = CAMPAIGN_SLUGS.map((slug) => ({
  variantKey: `campaign-${slug}`,
  context: "campaign" as const,
  entitySlug: slug,
  stepCount: DEFAULT_ONBOARDING_STEP_COUNT,
  generationHints: {
    instruction: "Conversion-focused onboarding: short, clear steps.",
  },
}));

const CITY_INDUSTRY_ONBOARDING_TEMPLATE: OnboardingVariantConfig = {
  variantKey: "city-industry",
  context: "city-industry",
  stepCount: DEFAULT_ONBOARDING_STEP_COUNT,
  generationHints: {
    instruction:
      "Onboarding for [city] + [industry]: e.g. Get set up for coffee delivery in Toronto.",
  },
};

/** All onboarding variant configs. */
export const ONBOARDING_VARIANT_CONFIGS: OnboardingVariantConfig[] = [
  DEFAULT_ONBOARDING,
  ...INDUSTRY_ONBOARDING_VARIANTS,
  ...SERVICE_AREA_ONBOARDING_VARIANTS.filter((v) => v.variantKey !== "default"),
  ...CAMPAIGN_ONBOARDING_VARIANTS,
  CITY_INDUSTRY_ONBOARDING_TEMPLATE,
];

export function getOnboardingVariantConfig(variantKey: string): OnboardingVariantConfig | null {
  return ONBOARDING_VARIANT_CONFIGS.find((c) => c.variantKey === variantKey) ?? null;
}

export function getOnboardingVariantConfigForEntity(
  context: OnboardingVariantConfig["context"],
  entitySlug?: string
): OnboardingVariantConfig | null {
  if (context === "default") return getOnboardingVariantConfig("default");
  if (context === "city-industry") return getOnboardingVariantConfig("city-industry");
  const found = ONBOARDING_VARIANT_CONFIGS.find(
    (c) => c.context === context && c.entitySlug === entitySlug
  );
  return found ?? null;
}
