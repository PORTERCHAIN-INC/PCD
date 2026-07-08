/**
 * Reusable authority / guides page framework for Porterchain.
 * Educational, practical pages that build trust and reinforce local logistics expertise.
 * All pages are internally linked and support a single CTA to the merchant wizard.
 */

import type { Locale } from "@/i18n/routing";
import {
  industrySlug,
  serviceAreaSlug,
  business,
  integrations,
  pricing,
  serviceAreas,
  contact,
} from "../routes";
import { INDUSTRY_PAGE_LABELS } from "../internal-linking";

export type AuthoritySection = {
  heading: string;
  /** One or more paragraphs (split by \n\n when rendering). */
  body: string;
};

export type AuthorityPage = {
  slug: string;
  /** H1 and meta title. */
  title: string;
  /** Meta description. */
  description: string;
  /** Lead paragraph; reinforces local logistics. */
  intro: string;
  sections: AuthoritySection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  extraLinks?: {
    path: "onboarding" | "workflow" | "integrations" | "pricing" | "serviceAreas" | "support";
    label: string;
  }[];
};

export type AuthorityLink = { href: string; label: string };

export const AUTHORITY_PAGES: AuthorityPage[] = [
  {
    slug: "how-porterchain-works",
    title: "How Porterchain works",
    description:
      "How Porterchain runs local delivery for merchants: one partner, recurring and same-day routes, full tracking. Built for GTA, Toronto, Ontario metros.",
    intro:
      "Porterchain is a local logistics partner for merchants with recurring or same-day delivery needs. We run the fleet and last mile in the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, and other Ontario regions. You get one partner, one dashboard, and full visibility from pickup to delivery — no fleet to run, no drivers to hire. This guide explains how we operate and what you can expect.",
    sections: [
      {
        heading: "One partner for recurring and same-day",
        body: "Whether you run weekly café drops, subscription boxes, pharmacy deliveries, or on-demand same-day runs, Porterchain handles both recurring and same-day in the same system. You submit orders or stops (via CSV or API); we align capacity, run the routes, and give you status and ETAs in one place. Our local operations teams know the zones we serve, so routing and time windows are built around real coverage in Toronto, the GTA, and Ontario metros.",
      },
      {
        heading: "Local operations, not a national network",
        body: "We focus on local delivery in the regions we serve. That means dedicated capacity and routing tuned to the GTA, Peel, Waterloo, London, Niagara, and surrounding areas. Traffic patterns, cut-offs, and vehicle fit are all aligned to local reality. When you need same-day or recurring delivery in these zones, you're not competing with long-haul or national volume — you get capacity and attention suited to local logistics.",
      },
      {
        heading: "Visibility and control",
        body: "Every run has full tracking from pickup to delivery. You see status and ETA in your dashboard, and you can share tracking links with your customers or partners. There are no black holes: once a stop is in our system, you know where it is and when it's expected. Reports and history are available so you can run operations with clarity.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "onboarding", label: "Merchant onboarding" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "delivery-operations-model",
    title: "Delivery operations model",
    description:
      "How Porterchain’s delivery operations work: capacity, routing, time windows, and local execution in the GTA and Ontario.",
    intro:
      "Porterchain’s operations are built around local execution. We match capacity to your volume and service areas, plan routes for efficiency and time windows, and run pickup and delivery with full visibility. This guide outlines our delivery operations model so you know how we work with merchants in the GTA, Toronto, and across Ontario.",
    sections: [
      {
        heading: "Capacity aligned to your volume and zones",
        body: "We don’t treat every run as a one-off. For recurring routes, we align drivers and vehicles to your schedule and zones so you get consistent capacity. Same-day runs use the same local fleet and ops; cut-offs and time windows are agreed so we can deliver on promises. Capacity is planned by region — Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara — so local knowledge drives routing and execution.",
      },
      {
        heading: "Routing and time windows",
        body: "Routes are built around your stops, time windows, and vehicle fit. Multi-stop runs are optimized for the zones we serve; we factor in traffic and geography so ETAs are realistic. You set the requirements (e.g. morning delivery for cafés, afternoon for patients); we execute within those windows. Same-day runs follow the same discipline: clear cut-offs and windows so you and your customers know what to expect.",
      },
      {
        heading: "Pickup to delivery, one chain",
        body: "From pickup at your location to handoff at the destination, every stop is tracked. Drivers are trained on handling and time windows; you get status updates and ETAs throughout. For industries with compliance or handling requirements (e.g. pharmacy, temperature-sensitive), we work with you during onboarding so operations meet your standards. The result is a single chain of custody and visibility across the GTA and Ontario.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "kitchener-waterloo", "niagara"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "onboarding", label: "Merchant onboarding" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "merchant-onboarding-guide",
    title: "Merchant onboarding guide",
    description:
      "How to onboard as a Porterchain merchant: volume, service areas, CSV or API, and what to expect. Get live in days, not weeks.",
    intro:
      "Onboarding with Porterchain is designed to be fast. We focus on your volume, service areas, and workflow so we can confirm coverage, align capacity, and get you live with tracking and reporting. Most merchants are set up within days. This guide walks you through what we need and what happens next.",
    sections: [
      {
        heading: "What we need from you",
        body: "We need your typical volume (e.g. stops per week or per run), the areas you deliver to (cities, neighbourhoods, or zones), and any time windows or special requirements. You can start with a spreadsheet or CSV; we’ll confirm the format and required fields. If you have compliance or handling needs (e.g. pharmacy, temperature-sensitive), we’ll capture those during onboarding. No need for a full integration on day one — many merchants start with CSV or email and add API later.",
      },
      {
        heading: "Coverage and capacity",
        body: "We confirm that we serve your delivery areas. We operate in the GTA (Toronto, Mississauga, Brampton, Vaughan, Markham, and surrounding), Kitchener-Waterloo, London, Niagara, Oshawa, and other Ontario regions. Once we’ve confirmed coverage, we align capacity to your schedule and agree on SLAs. You’ll know exactly where we deliver and what you can expect before you commit.",
      },
      {
        heading: "Going live",
        body: "Once we’re aligned, you get access to the dashboard and can start submitting orders or stops. Recurring routes are set up so you can send the same run each week (or on your cadence). Same-day options are available where we operate. You’ll have tracking and ETAs from the first run. We’ll walk you through any steps specific to your workflow so you’re confident from day one.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "integrations", label: "Integrations" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "route-and-tracking-overview",
    title: "Route and tracking overview",
    description:
      "How routes and tracking work with Porterchain: status, ETAs, and visibility from pickup to delivery in the GTA and Ontario.",
    intro:
      "Every Porterchain run has full tracking from pickup to delivery. You see status and ETA in your dashboard, and you can share tracking links with customers or partners. This guide explains how routes are managed and how tracking works so you can run operations with full visibility.",
    sections: [
      {
        heading: "How routes are built and run",
        body: "You submit stops (via CSV, API, or our tools); we build the route based on your time windows, vehicle fit, and the zones we serve. Multi-stop runs are optimized for the local area — Toronto, Mississauga, Brampton, or wherever you deliver. Drivers receive the route and run it with real-time updates, so status and ETAs stay accurate. Recurring routes follow the same process each cycle so you get consistent execution.",
      },
      {
        heading: "Status and ETAs",
        body: "From the moment a stop is picked up, you see its status and estimated delivery time. The dashboard shows progress across all runs; you can drill into any stop for detail. ETAs are updated as the route progresses, so you and your customers stay informed. No more guessing or chasing drivers for updates.",
      },
      {
        heading: "Sharing tracking with customers",
        body: "Every delivery can have a shareable tracking link. You send the link to your customer or partner; they see status and ETA without logging in. That reduces “where’s my order?” calls and keeps everyone aligned. Links work across the regions we serve — same experience in the GTA, Kitchener-Waterloo, London, Niagara, and beyond.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "kitchener-waterloo", "niagara"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "onboarding", label: "Merchant onboarding" },
      { path: "support", label: "Support" },
    ],
  },
  {
    slug: "support-and-issue-handling",
    title: "Support and issue handling",
    description:
      "How Porterchain support and issue handling work: when to contact us, how we handle problems, and operations support for merchants.",
    intro:
      "When something goes wrong or you have a question, we’re here to help. Porterchain support is built for operations: we understand delivery, routing, and the realities of local logistics in the GTA and Ontario. This guide explains how to get support and how we handle issues so you can run with confidence.",
    sections: [
      {
        heading: "When to contact support",
        body: "Contact us for anything that affects your delivery: a missed time window, a damaged or lost package, a driver or routing question, or a change to your run. We also help with onboarding, integration, and reporting. If you’re not sure whether something is a support issue, reach out — we’d rather clarify early than have a problem escalate. Our team is familiar with local operations in Toronto, Mississauga, Kitchener-Waterloo, London, Niagara, and the rest of our coverage.",
      },
      {
        heading: "How we handle issues",
        body: "We log every issue and track it to resolution. For service failures (e.g. late delivery, missed window), we investigate and work with you on next steps. Depending on the situation, that may include credits, reruns, or process changes. We don’t leave you in the dark: you’ll get updates and a clear path to resolution. For urgent problems (e.g. in-transit issue), we prioritize so operations can continue.",
      },
      {
        heading: "Reporting and escalation",
        body: "You can report an issue through our support channel or the report-issue flow. Include the run or stop reference so we can find it quickly. For recurring or systemic issues, we’ll work with you on root cause and prevention. Our goal is to keep your delivery running smoothly and to fix problems when they occur — so your local logistics stay reliable.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "support", label: "Support" },
      { path: "workflow", label: "How delivery works" },
      { path: "onboarding", label: "Merchant onboarding" },
    ],
  },
];

export function getAuthorityPageBySlug(slug: string): AuthorityPage | null {
  return AUTHORITY_PAGES.find((p) => p.slug === slug) ?? null;
}

export function getAllAuthoritySlugs(): string[] {
  return AUTHORITY_PAGES.map((p) => p.slug);
}

const EXTRA_PATH_TO_BUILDER: Record<string, (locale: Locale) => string> = {
  onboarding: business,
  workflow: business,
  integrations: integrations,
  pricing: pricing,
  serviceAreas: serviceAreas,
  support: contact,
};

export function buildAuthorityInternalLinks(
  locale: Locale,
  page: AuthorityPage
): { industry: AuthorityLink[]; serviceAreas: AuthorityLink[]; extra: AuthorityLink[] } {
  const industry = page.industrySlugs.map((s) => ({
    href: industrySlug(locale, s),
    label: INDUSTRY_PAGE_LABELS[s] ?? s.replace(/-/g, " "),
  }));

  const serviceAreasLinks = page.serviceAreaSlugs.map((s) => ({
    href: serviceAreaSlug(locale, s),
    label: s.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
  }));

  const extra =
    page.extraLinks?.map((e) => ({
      href: (EXTRA_PATH_TO_BUILDER[e.path] ?? (() => "#"))(locale),
      label: e.label,
    })) ?? [];

  return { industry, serviceAreas: serviceAreasLinks, extra };
}
