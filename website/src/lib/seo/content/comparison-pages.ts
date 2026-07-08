/**
 * Reusable comparison and alternatives page framework for Porterchain.
 * Compares Porterchain against broad alternatives (in-house, ad hoc courier,
 * unmanaged same-day, spreadsheet-only dispatch). No competitor naming;
 * messaging is credible and service-focused. SEO-friendly and conversion-supportive.
 */

import type { Locale } from "@/i18n/routing";
import {
  industrySlug,
  serviceAreaSlug,
  business,
  integrations,
  pricing,
  serviceAreas,
} from "../routes";
import { INDUSTRY_PAGE_LABELS } from "../internal-linking";

export type ComparisonRow = {
  /** Short label for the dimension (e.g. "Visibility", "Cost predictability"). */
  dimension: string;
  /** How Porterchain handles it. */
  porterchain: string;
  /** How the alternative typically works. */
  alternative: string;
};

export type ComparisonPage = {
  slug: string;
  /** H1 and meta title, e.g. "Porterchain vs. in-house delivery". */
  title: string;
  /** Meta description. */
  description: string;
  /** 1–2 paragraphs intro; credible, service-focused. */
  intro: string;
  /** Label for the alternative column (e.g. "In-house delivery"). */
  alternativeLabel: string;
  /** Comparison dimensions: Porterchain vs alternative. */
  comparisonRows: ComparisonRow[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  extraLinks?: {
    path: "onboarding" | "integrations" | "pricing" | "serviceAreas";
    label: string;
  }[];
};

export type ComparisonLink = { href: string; label: string };

export const COMPARISON_PAGES: ComparisonPage[] = [
  {
    slug: "in-house-delivery",
    title: "Porterchain vs. in-house delivery",
    description:
      "Compare managed delivery with Porterchain to running your own fleet. Visibility, cost predictability, and one partner for recurring and same-day delivery.",
    intro:
      "Many merchants start with in-house delivery when volume is low. As you grow, fleet costs, hiring, maintenance, and scheduling can become a distraction. Porterchain gives you one partner and one dashboard for recurring and same-day delivery — no fleet to run, no drivers to hire. You keep control over service areas and time windows; we handle capacity, routing, and last-mile execution. This comparison is factual and service-focused so you can decide what fits your volume and goals.",
    alternativeLabel: "In-house delivery",
    comparisonRows: [
      {
        dimension: "Visibility and tracking",
        porterchain:
          "One dashboard for status and ETAs; full visibility from pickup to delivery. You and your customers see when to expect delivery.",
        alternative:
          "Depends on your tools and drivers. Many in-house setups use phones and spreadsheets, so visibility is manual and often delayed.",
      },
      {
        dimension: "Cost predictability",
        porterchain:
          "Pricing aligned to stops, zones, and volume. Predictable cost without vehicle ownership, maintenance, or payroll for drivers.",
        alternative:
          "Fixed and variable costs: vehicles, fuel, insurance, wages, maintenance. Harder to scale up or down with demand.",
      },
      {
        dimension: "Recurring and same-day",
        porterchain:
          "Recurring routes (e.g. weekly café drops) and same-day options in one place. One partner for both patterns.",
        alternative:
          "You schedule and staff for both. Same-day often means overtime or ad hoc runs that are harder to optimize.",
      },
      {
        dimension: "Scaling",
        porterchain:
          "We align capacity to your volume. Add stops or areas without adding vehicles or hiring.",
        alternative:
          "Scaling usually means more vehicles and more drivers. Capital and hiring become the bottleneck.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "ad-hoc-courier",
    title: "Porterchain vs. ad hoc courier use",
    description:
      "Compare Porterchain’s managed recurring and same-day delivery with booking couriers one run at a time. Predictability, visibility, and one partner.",
    intro:
      "Booking a courier for each run works for occasional one-offs. For recurring or regular same-day delivery, ad hoc booking often means variable pricing, no single view of status, and time spent coordinating each run. Porterchain is built for merchants with recurring or regular volume: one partner, consistent capacity, and one place to see every run. You get predictable pricing and full tracking without chasing different couriers. Here’s how the two approaches compare.",
    alternativeLabel: "Ad hoc courier use",
    comparisonRows: [
      {
        dimension: "Pricing and predictability",
        porterchain:
          "Pricing tied to your volume and zones. One invoice, predictable cost per stop or route.",
        alternative:
          "Per-booking rates that can vary by demand, distance, and provider. Less predictable at scale.",
      },
      {
        dimension: "Visibility",
        porterchain:
          "One dashboard for all runs. Status and ETAs in one place for you and your customers.",
        alternative:
          "Tracking often depends on which courier you used. Multiple apps or links; no single view.",
      },
      {
        dimension: "Recurring routes",
        porterchain:
          "Recurring routes (e.g. weekly drops) are core. Same capacity, same partner, same process each time.",
        alternative:
          "Recurring means rebooking every time. Coordination and variability increase with volume.",
      },
      {
        dimension: "Time to run",
        porterchain:
          "Submit orders or stops (CSV or API); we run the route. No daily booking or driver hunting.",
        alternative:
          "Each run requires finding availability, booking, and communicating details. Time adds up with volume.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "unmanaged-same-day",
    title: "Porterchain vs. unmanaged same-day delivery",
    description:
      "Compare managed same-day delivery with Porterchain to unmanaged same-day workflows. Visibility, cut-offs, and one partner for recurring and on-demand.",
    intro:
      "Unmanaged same-day delivery often means coordinating drivers or couriers manually, with little visibility until delivery is done. Porterchain offers managed same-day in our service areas: you set cut-offs and time windows, we handle capacity and execution, and you get status and ETAs in one dashboard. Same-day works alongside recurring routes so one partner covers both. This comparison focuses on what changes when same-day is managed end-to-end.",
    alternativeLabel: "Unmanaged same-day workflows",
    comparisonRows: [
      {
        dimension: "Cut-offs and time windows",
        porterchain:
          "Agreed cut-offs and time windows. We align capacity so you know what’s possible and when.",
        alternative:
          "Often ad hoc: you find out at run time whether you can hit a window. Harder to promise customers.",
      },
      {
        dimension: "Visibility",
        porterchain:
          "Real-time status and ETAs. You and your customers see when to expect delivery.",
        alternative:
          "Updates are often manual or after the fact. Less ability to inform customers or adjust plans.",
      },
      {
        dimension: "Recurring + same-day",
        porterchain:
          "Recurring routes and same-day in one place. One partner, one process, one view.",
        alternative:
          "Recurring and same-day are usually separate workflows. More coordination and more gaps.",
      },
      {
        dimension: "Consistency",
        porterchain: "One process and one SLA. Same quality and visibility for every run.",
        alternative: "Depends on who’s running each run. Quality and communication can vary.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "niagara"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "spreadsheet-dispatch",
    title: "Porterchain vs. spreadsheet-only dispatch",
    description:
      "Compare Porterchain’s visibility and managed delivery to dispatch run only from spreadsheets. One dashboard, tracking, and support for CSV or API.",
    intro:
      "Spreadsheets are a practical way to list stops and share them with drivers or couriers. The gap is visibility: once the list is handed off, you often lose real-time status and ETAs. Porterchain supports CSV and spreadsheets for getting started, but every run gets full tracking and one dashboard. You keep your workflow; we add visibility, capacity, and one partner. Here’s how spreadsheet-only dispatch compares to managed delivery with visibility.",
    alternativeLabel: "Spreadsheet-only dispatch",
    comparisonRows: [
      {
        dimension: "Visibility after dispatch",
        porterchain:
          "Every run has status and ETA in one dashboard. You and your customers see progress without chasing updates.",
        alternative:
          "Stops are in a sheet; execution is elsewhere. Status often comes back manually or not at all.",
      },
      {
        dimension: "Submission",
        porterchain:
          "CSV upload or API. Same format for recurring runs; we run the route and provide tracking.",
        alternative:
          "Sheet is sent to drivers or a courier. No built-in tracking or single view of all runs.",
      },
      {
        dimension: "Scaling",
        porterchain:
          "Add volume or areas without changing how you submit. We handle capacity and routing.",
        alternative:
          "More volume usually means more sheets, more coordination, and the same visibility gap.",
      },
      {
        dimension: "Recurring routes",
        porterchain:
          "Recurring routes (e.g. weekly) with the same CSV or API. One partner, consistent process.",
        alternative:
          "Recurring means sending updated sheets each time. No unified view of history or performance.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "integrations", label: "Integrations" },
    ],
  },
];

export function getComparisonBySlug(slug: string): ComparisonPage | null {
  return COMPARISON_PAGES.find((p) => p.slug === slug) ?? null;
}

export function getAllComparisonSlugs(): string[] {
  return COMPARISON_PAGES.map((p) => p.slug);
}

export function buildComparisonInternalLinks(
  locale: Locale,
  page: ComparisonPage
): { industry: ComparisonLink[]; serviceAreas: ComparisonLink[]; extra: ComparisonLink[] } {
  const industry = page.industrySlugs.map((s) => ({
    href: industrySlug(locale, s),
    label: INDUSTRY_PAGE_LABELS[s] ?? s.replace(/-/g, " "),
  }));

  const serviceAreasLinks = page.serviceAreaSlugs.map((s) => ({
    href: serviceAreaSlug(locale, s),
    label: s.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  const pathToHref: Record<string, string> = {
    onboarding: business(locale),
    integrations: integrations(locale),
    pricing: pricing(locale),
    serviceAreas: serviceAreas(locale),
  };

  const extra =
    page.extraLinks?.map((e) => ({
      href: pathToHref[e.path] ?? "#",
      label: e.label,
    })) ?? [];

  return { industry, serviceAreas: serviceAreasLinks, extra };
}
