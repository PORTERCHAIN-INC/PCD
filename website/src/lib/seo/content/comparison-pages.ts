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
  {
    slug: "same-day-vs-scheduled",
    title: "Same-day vs scheduled B2B delivery",
    description:
      "Compare on-demand same-day capacity with scheduled recurring routes — when each pattern fits Ontario wholesale and jobsite programs.",
    intro:
      "Same-day delivery covers urgent overflow, missed windows, and customer commitments that cannot wait. Scheduled routes fit predictable wholesale, pharmacy, and construction supply lanes where stops repeat weekly or daily. Porterchain runs both under one partner with shared tracking and proof standards.",
    alternativeLabel: "Scheduled-only planning",
    comparisonRows: [
      {
        dimension: "Best for",
        porterchain:
          "Same-day for urgent overflow; scheduled for recurring stops — one partner covers both with shared visibility.",
        alternative:
          "Scheduled-only planning may leave no capacity when an urgent jobsite or pharmacy run appears same day.",
      },
      {
        dimension: "Visibility",
        porterchain:
          "One dashboard for scheduled and same-day runs with ETAs and proof on every stop.",
        alternative:
          "Splitting vendors splits visibility — status lives in different apps or phone calls.",
      },
    ],
    industrySlugs: ["construction-materials", "pharmacy-medical", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "onboarding", label: "How onboarding works" },
    ],
  },
  {
    slug: "cargo-van-vs-sprinter-van",
    title: "Cargo van vs Sprinter van for B2B delivery",
    description:
      "Choose cargo van or Sprinter capacity for Ontario B2B runs — payload, access, and jobsite fit.",
    intro:
      "Cargo vans handle parcels, totes, and light trade freight across the GTA with easier urban access. Sprinter-class vans add height and payload for longer wholesale lanes and palletized freight that still needs van maneuverability. Porterchain quotes the right vehicle class for your stops.",
    alternativeLabel: "One-size vehicle booking",
    comparisonRows: [
      {
        dimension: "Payload and cube",
        porterchain:
          "Cargo van for lighter multi-stop B2B; Sprinter when height or payload needs exceed cargo van limits.",
        alternative:
          "One vehicle class for every run can mean failed loads or paying for unused capacity.",
      },
      {
        dimension: "Quote process",
        porterchain:
          "Describe freight dimensions and stops — we confirm vehicle class in writing before dispatch.",
        alternative:
          "Self-serve booking without class guidance often leads to wrong vehicle on arrival.",
      },
    ],
    industrySlugs: ["electrical-distribution", "plumbing-supply", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "vaughan"],
    extraLinks: [
      { path: "serviceAreas", label: "Service areas" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "dedicated-vs-shared-capacity",
    title: "Dedicated vehicle vs shared courier capacity",
    description:
      "Compare dedicated vehicle programs with shared same-day courier capacity for Ontario B2B shippers.",
    intro:
      "Dedicated capacity fits predictable high-volume lanes. Shared courier capacity fits overflow and uneven demand. Porterchain can run both patterns under one partner — choose based on volume stability, not marketing labels.",
    alternativeLabel: "Shared ad hoc courier only",
    comparisonRows: [
      {
        dimension: "Best fit",
        porterchain:
          "Dedicated routes for recurring volume; shared capacity for overflow and spikes — one partner for both.",
        alternative:
          "Shared-only booking often lacks reserved capacity when volume spikes mid-week.",
      },
      {
        dimension: "Cost structure",
        porterchain:
          "Dedicated programs quoted to lane volume; shared runs quoted per request with written confirmation.",
        alternative: "Per-booking rates without reserved capacity can swing with demand.",
      },
      {
        dimension: "Accountability",
        porterchain:
          "Same proof and escalation standards whether the vehicle is dedicated or shared that day.",
        alternative: "Different couriers mean different proof quality and escalation paths.",
      },
    ],
    industrySlugs: ["construction-materials", "electrical-distribution", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "sprinter-vs-box-truck",
    title: "Sprinter van vs box truck for B2B delivery",
    description:
      "When Sprinter-class vans beat box trucks — and when pallet freight needs a cube truck across the GTA.",
    intro:
      "Sprinter-class vans balance height and urban access. Box trucks win for pallets, construction materials, and dock freight. Porterchain quotes the class that fits your stops so you do not oversize every run.",
    alternativeLabel: "Always booking box truck",
    comparisonRows: [
      {
        dimension: "Freight profile",
        porterchain:
          "Sprinter for tall non-pallet freight and wholesale cases; box truck for pallets and jobsite drops.",
        alternative: "Box truck on every run raises cost when freight would fit a van.",
      },
      {
        dimension: "Access",
        porterchain:
          "Sprinter for tighter urban and retail access; box truck when docks and yards allow.",
        alternative: "Oversized trucks on tight sites cause failed deliveries and redelivery.",
      },
      {
        dimension: "Quote process",
        porterchain: "Share dimensions and pallet count — we confirm class before dispatch.",
        alternative:
          "Guessing vehicle class without a written confirmation risks wrong capacity on arrival.",
      },
    ],
    industrySlugs: ["construction-materials", "plumbing-supply", "electrical-distribution"],
    serviceAreaSlugs: ["toronto", "vaughan", "hamilton"],
    extraLinks: [
      { path: "serviceAreas", label: "Service areas" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "api-vs-manual-dispatch",
    title: "API booking vs manual dispatch",
    description:
      "Compare Porterchain API booking with phone/email/CSV manual dispatch for Ontario volume growth.",
    intro:
      "Manual dispatch works early. As stop count grows, API or structured CSV reduces errors and lag. Porterchain supports both — start manual, move to API when volume justifies it.",
    alternativeLabel: "Manual phone and email only",
    comparisonRows: [
      {
        dimension: "Speed to book",
        porterchain:
          "API and CSV submit stops in bulk; manual intake remains available for low volume and exceptions.",
        alternative: "Every run requires human coordination — latency grows with volume.",
      },
      {
        dimension: "Error rate",
        porterchain:
          "Structured fields and validation reduce address and window mistakes before dispatch.",
        alternative:
          "Hand-typed details in chat or email are easy to mis-copy under time pressure.",
      },
      {
        dimension: "Visibility",
        porterchain: "Booked runs land in one dashboard with tracking regardless of intake path.",
        alternative: "Manual booking often leaves status scattered across inboxes and texts.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Onboarding" },
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
