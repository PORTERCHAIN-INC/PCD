/**
 * Page templates for SEO content expansion.
 * Defines which entity slots and section blocks each page type uses.
 * Safe for AI-assisted generation: explicit structure and variant context.
 */

import type { PageTemplate } from "./types";

/** Templates for existing and future page types. Order of sectionBlocks implies display order. */
export const PAGE_TEMPLATES: PageTemplate[] = [
  {
    pageType: "industry",
    description: "Industry (niche) landing page: e.g. coffee roasters, pharmacy, cosmetics.",
    entitySlots: ["industry"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "vehicleFit",
      "workflow",
      "coverage",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "industry",
  },
  {
    pageType: "service-area",
    description: "Service area (city/region) page: e.g. Toronto, Mississauga, Kitchener-Waterloo.",
    entitySlots: ["serviceArea"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "industries",
      "workflow",
      "coverage",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "service-area",
  },
  {
    pageType: "service-area-index",
    description: "Index page listing all service areas.",
    entitySlots: [],
    sectionBlocks: ["meta"],
    variantContext: "default",
  },
  {
    pageType: "campaign",
    description:
      "Campaign landing page: conversion-focused, e.g. recurring-delivery, coffee-roasters.",
    entitySlots: ["campaign"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "workflow",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "campaign",
  },
  {
    pageType: "city",
    description:
      "Future: city-only page (alias or variant of service-area with city-focused copy).",
    entitySlots: ["serviceArea"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "industries",
      "workflow",
      "coverage",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "service-area",
  },
  {
    pageType: "city-industry",
    description: "Future: city + industry combined page, e.g. coffee delivery in Toronto.",
    entitySlots: ["serviceArea", "industry"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "workflow",
      "coverage",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "city-industry",
  },
  {
    pageType: "service",
    description:
      "Future: generic service page, e.g. same-day delivery, recurring delivery (no city/industry).",
    entitySlots: ["service"],
    sectionBlocks: [
      "meta",
      "hero",
      "painPoints",
      "solution",
      "workflow",
      "onboarding",
      "faq",
      "cta",
      "inquiry",
    ],
    variantContext: "default",
  },
];

export function getPageTemplate(pageType: PageTemplate["pageType"]): PageTemplate | null {
  return PAGE_TEMPLATES.find((t) => t.pageType === pageType) ?? null;
}

export function getPageTemplatesForEntitySlot(
  slot: "industry" | "serviceArea" | "campaign" | "service"
): PageTemplate[] {
  return PAGE_TEMPLATES.filter((t) => t.entitySlots.includes(slot));
}
