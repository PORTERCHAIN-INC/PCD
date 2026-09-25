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
    "construction materials delivery GTA",
    "building supply same-day",
    "jobsite delivery Toronto",
    "lumber delivery Mississauga",
    "drywall delivery GTA",
    "pallet delivery contractors",
  ],
  "electrical-distribution": [
    "electrical distributor delivery",
    "electrical wholesaler same-day GTA",
    "wire and cable delivery Toronto",
    "panel delivery contractors",
    "electrical supply house logistics",
  ],
  "plumbing-supply": [
    "plumbing supply delivery GTA",
    "pipe and fitting same-day",
    "fixture delivery contractors",
    "plumbing wholesaler logistics Toronto",
  ],
  "coffee-roasters": [
    "coffee wholesale delivery GTA",
    "roaster café delivery Toronto",
    "coffee subscription logistics",
    "bean delivery cafés Ontario",
  ],
  "pharmacy-medical": [
    "pharmacy delivery GTA",
    "medical supply same-day Toronto",
    "clinic sample logistics",
    "B2B pharmacy courier overflow",
    "temperature-aware medical capacity",
  ],
  cosmetics: [
    "cosmetics delivery GTA",
    "beauty wholesale same-day",
    "D2C beauty logistics Toronto",
    "salon supply delivery Ontario",
  ],
  chocolate: [
    "chocolate wholesale delivery GTA",
    "confectionery same-day Toronto",
    "temperature-sensitive chocolate logistics",
    "candy distributor capacity Ontario",
  ],
  "lab-sample-delivery": [
    "lab sample delivery GTA",
    "specimen courier Toronto",
    "clinic to lab same-day",
    "diagnostic sample logistics Ontario",
  ],
  ecommerce: [
    "e-commerce last mile GTA",
    "D2C same-day Toronto",
    "parcel overflow capacity",
    "fulfillment delivery partners Ontario",
  ],
  "hvac-mechanical": [
    "HVAC parts delivery GTA",
    "mechanical contractor same-day",
    "furnace and A/C parts logistics",
  ],
  "automotive-parts": [
    "auto parts delivery GTA",
    "dealer parts same-day Toronto",
    "aftermarket parts logistics",
  ],
  manufacturing: [
    "manufacturing parts delivery GTA",
    "plant-to-plant capacity Ontario",
    "industrial same-day logistics",
  ],
  "retail-replenishment": [
    "retail replenishment delivery GTA",
    "store restock same-day Toronto",
    "multi-stop retail capacity",
  ],
  "food-distribution": [
    "food distribution delivery GTA",
    "wholesale food same-day Toronto",
    "cold-chain overflow capacity Ontario",
  ],
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
        ? ["pharmacy", "medical", "patients", "B2B", "clinics"]
        : slug === "construction-materials"
          ? ["distributors", "contractors", "jobsite", "building supply"]
          : slug === "electrical-distribution"
            ? ["electrical wholesalers", "contractors", "distributors"]
            : slug === "plumbing-supply"
              ? ["plumbing wholesalers", "contractors", "supply houses"]
              : slug === "ecommerce"
                ? ["e-commerce", "D2C", "online retail", "last mile"]
                : slug === "coffee-roasters"
                  ? ["roasters", "cafés", "wholesale coffee", "subscriptions"]
                  : slug === "cosmetics"
                    ? ["beauty brands", "salons", "D2C", "wholesale"]
                    : slug === "chocolate"
                      ? ["confectionery", "wholesale chocolate", "specialty food"]
                      : slug === "lab-sample-delivery"
                        ? ["labs", "clinics", "diagnostics", "specimen logistics"]
                        : undefined,
    tone:
      slug === "cosmetics"
        ? ["beauty", "subscription", "D2C", "retail"]
        : slug === "chocolate"
          ? ["temperature-aware", "specialty food", "wholesale"]
          : slug === "lab-sample-delivery"
            ? ["chain of custody", "time-critical", "clinical"]
            : undefined,
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
