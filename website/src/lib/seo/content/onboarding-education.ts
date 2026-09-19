/**
 * Merchant onboarding education cluster for Porterchain.
 * SEO and sales-enabling content: getting started, order data, CSV, API,
 * admin-assisted onboarding, first route expectations.
 * All CTAs point to the existing merchant wizard only.
 */

import type { Locale } from "@/i18n/routing";
import { industrySlug, serviceAreaSlug, business, integrations, serviceAreas } from "../routes";
import { INDUSTRY_PAGE_LABELS } from "../internal-linking";

export type OnboardingEducationSection = {
  heading: string;
  body: string;
};

export type OnboardingEducationPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  sections: OnboardingEducationSection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  /** Other pages in this cluster to link to (slugs). */
  relatedClusterSlugs?: string[];
  extraLinks?: { path: "onboarding" | "integrations" | "serviceAreas"; label: string }[];
};

export type OnboardingEducationLink = { href: string; label: string };

export const ONBOARDING_EDUCATION_PAGES: OnboardingEducationPage[] = [
  {
    slug: "getting-started",
    title: "Getting started with Porterchain",
    description:
      "What to expect when you onboard with Porterchain: timeline, what we need from you, and how to go live. Days, not weeks.",
    intro:
      "Getting started with Porterchain is designed to be straightforward. We need your volume, service areas, and how you want to submit orders (CSV, email, or API). We confirm we serve your delivery zones, align capacity, and get you live with tracking from day one. Most merchants are set up within days. This page walks you through what to expect so you can prepare and move quickly.",
    sections: [
      {
        heading: "What we need from you",
        body: "We need your typical delivery volume (e.g. stops per week or per run), the areas you deliver to (cities, neighbourhoods, or zones), and any time windows or special requirements. You don’t need a full integration to start — many merchants begin with a spreadsheet or CSV. We’ll confirm the format and get you running. If you have compliance or handling needs (e.g. pharmacy, temperature-sensitive), we capture those early so we’re ready when you go live.",
      },
      {
        heading: "Timeline: days, not weeks",
        body: "Once we have your volume and service areas, we confirm coverage and align capacity. Setup typically takes days: we’re not building custom software for you, we’re connecting your workflow to our operations. You’ll have access to the dashboard and can submit your first run as soon as we’re aligned. Recurring routes are set up so you can repeat the same process each week or on your cadence.",
      },
      {
        heading: "No long forms",
        body: "We focus on what we need to get you delivering. There’s no lengthy application or multi-step form. We’ll ask for the essentials, confirm fit and pricing, and get you live. If you prefer to have us set things up for you (e.g. admin-assisted onboarding), we can do that too — it’s all designed so you can start quickly and scale when ready.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london"],
    relatedClusterSlugs: ["preparing-order-data", "using-csv-upload", "first-route-expectations"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "preparing-order-data",
    title: "Preparing order data for delivery",
    description:
      "What order and stop data Porterchain needs: addresses, contacts, time windows, and references. Tips for clean data and smooth routes.",
    intro:
      "Good order data makes routing and delivery reliable. We need delivery address, contact details, and any time window or reference you use. This page explains what to prepare so your first run — and every run after — goes smoothly. Whether you submit via CSV or API, the same data principles apply.",
    sections: [
      {
        heading: "Required fields",
        body: "Every stop needs a delivery address we can geocode (street, city, postal code). We also need a contact name and phone or email so the driver and recipient can coordinate. If you have time windows (e.g. 9am–12pm), include them — we’ll plan routes around them. Reference or order IDs help you match our tracking back to your system. We’ll give you a template or spec that lists required and optional fields so you can align your export or API payload.",
      },
      {
        heading: "Data quality tips",
        body: "Clean addresses reduce failed geocoding and wrong locations. Use a consistent format for city and postal code; avoid abbreviations unless we’ve agreed on them. Duplicate or near-duplicate stops (same address, same day) can often be merged — we can advise. If you have special instructions (e.g. gate code, leave at door), include them in a notes field. The better the data, the smoother the route and the fewer surprises.",
      },
      {
        heading: "Recurring vs one-off",
        body: "For recurring routes, the same structure applies every run: you send an updated list of stops (e.g. weekly café drops) and we run the route. For one-off or same-day runs, the process is the same — just different timing. We’ll confirm cut-offs and how to submit so your data lands in the right run.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: ["using-csv-upload", "api-onboarding", "getting-started"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "integrations", label: "Integrations" },
    ],
  },
  {
    slug: "using-csv-upload",
    title: "Using CSV upload for orders",
    description:
      "How to submit orders via CSV: template, columns, and workflow. Start with CSV and add API when you're ready.",
    intro:
      "Many merchants manage orders or stops in spreadsheets. We support CSV upload so you can send us runs without building an integration first. You get a template or specification; you fill it, upload (or email), and we run the route. This page covers how CSV upload works and how to use it for recurring or one-off delivery.",
    sections: [
      {
        heading: "Template and columns",
        body: "We provide a CSV template or spec with the required columns: delivery address (or street, city, postal), contact name, phone or email, and any time window or reference ID. Optional columns might include notes, special instructions, or weight. Once you’re set up, you can reuse the same format for every run. We’ll confirm the exact columns and any rules (e.g. date format, phone format) during onboarding so your file is accepted every time.",
      },
      {
        heading: "How to submit",
        body: "You upload the CSV through our portal or send it by email, depending on how we’ve set you up. The file is validated and turned into stops for the run. You’ll get confirmation and can track the route in your dashboard. For recurring routes, you send an updated file each cycle (e.g. every Monday for Tuesday delivery). Same process, same format — no need to re-enter data manually.",
      },
      {
        heading: "Moving to API later",
        body: "CSV is a great way to start. When you’re ready to automate, we support API so your system can push orders directly. Many merchants start with CSV and add API when their volume or workflow justifies it. We’ll help with the transition so there’s no disruption — same data, same routing, just a different submission method.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    relatedClusterSlugs: ["preparing-order-data", "api-onboarding", "getting-started"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "integrations", label: "Integrations" },
    ],
  },
  {
    slug: "api-onboarding",
    title: "API onboarding for delivery",
    description:
      "How to onboard with the Porterchain API: authentication, order and stop payloads, and going live. For merchants ready to automate.",
    intro:
      "When you’re ready to send orders programmatically, we offer an API for creating and managing stops and runs. You authenticate, post your payload, and we confirm and run the route. This page explains what’s involved in API onboarding so you can plan integration and go live with confidence.",
    sections: [
      {
        heading: "When to use API",
        body: "API is ideal when you have a system that already holds orders (e.g. e‑commerce, ERP, or internal tools) and you want to push delivery data to us without manual export or CSV. It’s also useful for same-day or high-frequency runs where manual uploads don’t scale. If you’re starting out, CSV is often faster to get live; you can add API when your volume or workflow demands it.",
      },
      {
        heading: "What we provide",
        body: "We give you API documentation, authentication (e.g. API key or OAuth, depending on our current offering), and endpoints for creating stops and runs. You’ll send the same data you’d put in a CSV: address, contact, time window, reference. We’ll confirm the exact schema and any webhooks or callbacks (e.g. delivery status) so your system stays in sync. Integration support is part of onboarding so you’re not on your own.",
      },
      {
        heading: "Going live",
        body: "We’ll work with you through a test or staging phase so you can validate payloads and responses before going live. Once we’re both confident, you switch to production and start sending real runs. We’ll monitor the first few runs and help with any issues. Same tracking and visibility as CSV — just automated submission.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "kitchener-waterloo"],
    relatedClusterSlugs: ["using-csv-upload", "preparing-order-data", "admin-assisted-onboarding"],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "How onboarding works" },
    ],
  },
  {
    slug: "admin-assisted-onboarding",
    title: "Admin-assisted onboarding",
    description:
      "When we set up your account and first runs for you. Handoff, first route, and what to expect with admin-assisted onboarding.",
    intro:
      "If you prefer not to configure everything yourself, we can do it for you. Admin-assisted onboarding means our team sets up your account, confirms your data format, and may run your first route with you on the line. It’s ideal when you want to get live quickly without touching CSV templates or API docs. This page explains how it works and when it’s a fit.",
    sections: [
      {
        heading: "When we do it",
        body: "We offer admin-assisted onboarding when you’d rather have us handle the initial setup. You share your volume, service areas, and a sample of your order data (e.g. a spreadsheet or export). We’ll map it to our format, configure your account, and walk you through the first run. This is especially helpful if your data is in an unusual format or you have many one-off questions — we answer them and get you live.",
      },
      {
        heading: "Setup and handoff",
        body: "We’ll set up your dashboard access, confirm how you’ll submit orders (CSV or API), and run a test or first route. You’ll see tracking and ETAs from day one. After the first run, we hand off so you can run future routes yourself — with the same template or API you’ll use going forward. You’re not dependent on us for every run; we just get you over the line the first time.",
      },
      {
        heading: "What you need to provide",
        body: "You still need to provide the same essentials: volume, service areas, and order data (or a sample). We’re doing the configuration and first-run support, not the data entry. Once you’re live, you can switch to your own CSV uploads or API when ready.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "london", "niagara"],
    relatedClusterSlugs: ["getting-started", "first-route-expectations", "using-csv-upload"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "first-route-expectations",
    title: "First route expectations",
    description:
      "What to expect on your first Porterchain run: tracking from day one, driver execution, and how we work with you after launch.",
    intro:
      "Your first route with Porterchain is a real run — we don’t do fake dry runs. You’ll see tracking and ETAs from the moment the driver starts, and you can share tracking links with your customers. This page sets expectations so you know what to watch for and how we’ll support you after the first run.",
    sections: [
      {
        heading: "Tracking from day one",
        body: "From the first pickup, every stop has status and ETA in your dashboard. You and your customers can see progress in real time. There’s no “learning run” where visibility is limited — you get the same experience from the first route as you will on your hundredth. If anything looks wrong, you can reach out and we’ll help.",
      },
      {
        heading: "Driver execution",
        body: "Our drivers run the route with the same tools and standards we use for all merchants. They’ll follow time windows and delivery instructions you’ve provided. If there’s an issue (e.g. closed business, wrong address), we’ll communicate and resolve it. The first run is a chance to validate addresses and instructions so future runs are even smoother.",
      },
      {
        heading: "After the first run",
        body: "We’ll debrief if needed and answer any questions. You’ll have a clear view of what worked and what to adjust (e.g. data format, time windows). From there, you’re set for recurring or same-day runs as planned. We’re here for support and optimization as you scale.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "niagara"],
    relatedClusterSlugs: ["getting-started", "admin-assisted-onboarding", "preparing-order-data"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
];

export function getOnboardingEducationBySlug(slug: string): OnboardingEducationPage | null {
  return ONBOARDING_EDUCATION_PAGES.find((p) => p.slug === slug) ?? null;
}

export function getAllOnboardingEducationSlugs(): string[] {
  return ONBOARDING_EDUCATION_PAGES.map((p) => p.slug);
}

const EXTRA_PATH_BUILDER: Record<string, (locale: Locale) => string> = {
  onboarding: business,
  integrations: integrations,
  serviceAreas: serviceAreas,
};

export function buildOnboardingEducationInternalLinks(
  locale: Locale,
  page: OnboardingEducationPage,
  slugBuilder: (locale: Locale, s: string) => string
): {
  industry: OnboardingEducationLink[];
  serviceAreas: OnboardingEducationLink[];
  extra: OnboardingEducationLink[];
  cluster: OnboardingEducationLink[];
} {
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
      href: (EXTRA_PATH_BUILDER[e.path] ?? (() => "#"))(locale),
      label: e.label,
    })) ?? [];

  const cluster = (page.relatedClusterSlugs ?? [])
    .map((s) => {
      const p = getOnboardingEducationBySlug(s);
      return p ? { href: slugBuilder(locale, s), label: p.title } : null;
    })
    .filter(Boolean) as OnboardingEducationLink[];

  return { industry, serviceAreas: serviceAreasLinks, extra, cluster };
}
