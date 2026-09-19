/**
 * Industry (niche) config for SEO content expansion.
 * Aligns with lib/niche-landing.ts and messages.nicheLanding.*
 */

import type { IndustryConfig } from "./types";
import { NICHE_SLUGS, NICHE_MESSAGE_KEYS } from "../niche-landing";
import type { NicheSlug } from "../niche-landing";

const LABELS: Record<NicheSlug, string> = {
  "construction-materials": "Construction materials",
  "electrical-distribution": "Electrical distribution",
  "plumbing-supply": "Plumbing supply",
  "coffee-roasters": "Coffee roasters",
  "pharmacy-medical": "Pharmacy & medical",
  cosmetics: "Cosmetics & beauty",
  chocolate: "Chocolate & confectionery",
  "lab-sample-delivery": "Lab sample delivery",
  ecommerce: "E-commerce delivery",
  "hvac-mechanical": "HVAC & mechanical (draft)",
  "automotive-parts": "Automotive parts (draft)",
  manufacturing: "Manufacturing (draft)",
  "retail-replenishment": "Retail replenishment (draft)",
  "food-distribution": "Food distribution (draft)",
};

const KEYWORDS: Partial<Record<NicheSlug, string[]>> = {
  "construction-materials": [
    "construction materials",
    "building supply",
    "jobsite delivery",
    "lumber",
    "drywall",
    "pallet delivery",
  ],
  "electrical-distribution": [
    "electrical distributor",
    "electrical wholesaler",
    "wire delivery",
    "panel delivery",
    "electrical supply",
  ],
  "plumbing-supply": ["plumbing supply", "pipe delivery", "fixture courier", "plumbing wholesaler"],
  "coffee-roasters": ["coffee", "roasters", "cafés", "subscription", "wholesale"],
  ecommerce: ["e-commerce", "last mile", "D2C", "parcel delivery", "fulfillment"],
};

/** Industry configs for all niches. Used for industry pages and city-industry page generation. */
export const INDUSTRY_CONFIGS: IndustryConfig[] = NICHE_SLUGS.map((slug) => ({
  id: `industry-${slug}`,
  slug,
  messageKey: NICHE_MESSAGE_KEYS[slug],
  label: LABELS[slug],
  generationHints: {
    keywords: KEYWORDS[slug],
    audience:
      slug === "pharmacy-medical"
        ? ["pharmacy", "medical", "patients", "B2B"]
        : slug === "construction-materials"
          ? ["distributors", "contractors", "jobsite", "building supply"]
          : slug === "electrical-distribution"
            ? ["electrical wholesalers", "contractors", "distributors"]
            : slug === "plumbing-supply"
              ? ["plumbing wholesalers", "contractors", "supply houses"]
              : slug === "ecommerce"
                ? ["e-commerce", "D2C", "online retail", "last mile"]
                : undefined,
    tone: slug === "cosmetics" ? ["beauty", "subscription", "D2C", "retail"] : undefined,
  },
}));

export function getIndustryConfig(slug: string): IndustryConfig | null {
  const found = INDUSTRY_CONFIGS.find((c) => c.slug === slug);
  return found ?? null;
}

export function getIndustryConfigByMessageKey(messageKey: string): IndustryConfig | null {
  const found = INDUSTRY_CONFIGS.find((c) => c.messageKey === messageKey);
  return found ?? null;
}
