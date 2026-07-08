/**
 * Integrations education cluster for Porterchain.
 * Practical content: CSV delivery uploads, API order ingestion,
 * EDI-ready workflows, operational setup for merchants.
 * Links to merchant onboarding and integrations pages. All CTAs = merchant wizard only.
 */

import type { Locale } from "@/i18n/routing";
import { industrySlug, serviceAreaSlug, business, integrations, serviceAreas } from "../routes";
import { INDUSTRY_PAGE_LABELS } from "../internal-linking";

export type IntegrationsEducationSection = {
  heading: string;
  body: string;
};

export type IntegrationsEducationPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  sections: IntegrationsEducationSection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  relatedClusterSlugs?: string[];
  extraLinks?: { path: "onboarding" | "integrations" | "serviceAreas"; label: string }[];
};

export type IntegrationsEducationLink = { href: string; label: string };

export const INTEGRATIONS_EDUCATION_PAGES: IntegrationsEducationPage[] = [
  {
    slug: "csv-delivery-uploads",
    title: "CSV delivery uploads",
    description:
      "How to submit delivery orders via CSV: template, columns, and workflow. Practical guide for recurring and one-off runs.",
    intro:
      "CSV upload is the simplest way to send us delivery orders. You use a template we provide, fill in your stops (address, contact, time window), and upload the file or send it by email. We turn it into a run and you track it in your dashboard. No API or integration required to start. This page explains how it works and what to expect.",
    sections: [
      {
        heading: "What you get",
        body: "We give you a CSV template or specification with the columns we need: delivery address (or street, city, postal code), contact name, phone or email, and optional fields like time window, reference ID, and notes. You export or build your list in that format. Once you’re set up, the same template works for every run — recurring or one-off. We’ll confirm the exact format during onboarding so there’s no guesswork.",
      },
      {
        heading: "How to submit",
        body: "You upload the file through our portal or send it by email, depending on your setup. We validate the file and create the stops for the run. You get confirmation and can track the route in your dashboard. For recurring routes (e.g. weekly café drops), you send an updated CSV each cycle. Cut-offs and timing are agreed so your run is planned correctly. If something in the file doesn’t pass validation, we’ll let you know so you can fix and resend.",
      },
      {
        heading: "When CSV is a fit",
        body: "CSV works well when your volume is manageable and you’re comfortable exporting from a spreadsheet or system. Many merchants start with CSV and add API later when they want to automate. We don’t promise unlimited file size or instant processing for every edge case — we’ll set clear expectations for your volume and turnaround so you know what to expect.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    relatedClusterSlugs: ["api-order-ingestion", "operational-setup-merchants"],
    extraLinks: [
      { path: "onboarding", label: "Merchant onboarding" },
      { path: "integrations", label: "Integrations" },
    ],
  },
  {
    slug: "api-order-ingestion",
    title: "API order ingestion",
    description:
      "How to send delivery orders to Porterchain via API: authentication, payload, and what we support. Practical overview for technical teams.",
    intro:
      "When you’re ready to push orders from your system to ours, we offer an API for creating stops and runs. You authenticate, send your payload with address and contact data, and we confirm and plan the route. This page gives a practical overview of what’s involved — we don’t overpromise; we outline what we support so you can plan your integration.",
    sections: [
      {
        heading: "What the API does",
        body: "The API lets you create delivery stops and runs programmatically. You send the same data you’d put in a CSV: delivery address, contact, time window, reference. We validate, geocode where needed, and add the stops to a run. You get a response with identifiers so you can track status in your dashboard or via webhooks if we support them for your account. We’ll provide documentation and a clear schema so your team can integrate without surprises.",
      },
      {
        heading: "Authentication and environment",
        body: "You’ll get credentials (e.g. API key) and use them to authenticate requests. We may offer a sandbox or test environment so you can validate payloads before going live. Going live means switching to production credentials and following our rate limits and conventions. We’ll confirm what’s available for your account during onboarding.",
      },
      {
        heading: "What we don’t promise",
        body: "We don’t claim to support every possible integration pattern or legacy format. Our API is designed for delivery order ingestion — structured address and contact data, time windows, references. If you have unusual requirements (e.g. custom fields, complex multi-leg logic), we’ll discuss feasibility during onboarding rather than overpromising. The goal is a reliable, maintainable integration that fits how we run delivery.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "kitchener-waterloo"],
    relatedClusterSlugs: [
      "csv-delivery-uploads",
      "edi-ready-workflows",
      "operational-setup-merchants",
    ],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Merchant onboarding" },
    ],
  },
  {
    slug: "edi-ready-workflows",
    title: "EDI-ready workflows",
    description:
      "How Porterchain can fit into EDI-style workflows: structured data, consistent formats, and what we support. Practical, no overpromising.",
    intro:
      "Some merchants operate in environments where orders or ship notices come from EDI or other structured systems. We don’t run a full EDI platform — we run delivery. What we can do is accept structured order data (via API or a defined file format) that aligns with how you already work. This page explains how we fit into EDI-ready workflows without overpromising capabilities we don’t have.",
    sections: [
      {
        heading: "Structured data in, delivery out",
        body: "If your orders are already in a structured form (e.g. from an ERP, WMS, or EDI pipeline), we can often consume that data via API or a mapped file format. We need delivery address, contact, time window, and reference — the same core fields as CSV or API. We don’t translate raw EDI ourselves; the expectation is that you (or your middleware) produce a payload or file we support. We’ll confirm the format and mapping during onboarding.",
      },
      {
        heading: "Consistent formats and timing",
        body: "Recurring EDI-style workflows often depend on consistent formats and cut-offs. We can agree on a fixed schema and timing (e.g. file or API batch by a certain time) so your pipeline feeds our system predictably. Status and proof of delivery can be exposed back via API or report so your downstream systems stay in sync. We’ll be clear about what we support so you can design your workflow accordingly.",
      },
      {
        heading: "What “EDI-ready” means here",
        body: "“EDI-ready” here means we can work with structured, repeatable data that fits our delivery model — not that we implement every EDI standard or transaction set. If you have specific EDI requirements (e.g. 856, 210), we’ll discuss how your data can be translated into what we ingest. We’d rather set clear boundaries than promise support we can’t deliver.",
      },
    ],
    industrySlugs: ["pharmacy-medical", "coffee-roasters", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london"],
    relatedClusterSlugs: ["api-order-ingestion", "operational-setup-merchants"],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Merchant onboarding" },
    ],
  },
  {
    slug: "operational-setup-merchants",
    title: "Operational setup for merchants",
    description:
      "How to set up your operations for Porterchain: cut-offs, run cadence, and handoff. Practical guide so delivery runs smoothly.",
    intro:
      "Getting delivery to run smoothly depends on how you set up your operations: when you send orders, how you handle cut-offs, and how you hand off to us. This page covers practical setup so your runs are consistent and predictable. We don’t promise to fix every operational issue — we outline what works so you can align your process.",
    sections: [
      {
        heading: "Cut-offs and run cadence",
        body: "We agree on cut-off times and run cadence (e.g. same-day, next-day, or recurring weekly). You need to send your order data (CSV or API) by the cut-off so we can plan the route and assign capacity. Missing the cut-off may mean your orders move to the next run — we’ll confirm the policy for your account. Having a clear cadence (e.g. “every Monday we run Tuesday delivery”) helps both sides plan.",
      },
      {
        heading: "Handoff and validation",
        body: "When you send data, we validate it and may geocode addresses. If something fails (e.g. bad address, missing contact), we’ll surface it so you can correct and resend where possible. The handoff point (portal upload, email, or API) is agreed at onboarding. We don’t promise real-time validation for every edge case — we’ll set expectations for turnaround and error handling so you know what to expect.",
      },
      {
        heading: "Ongoing operations",
        body: "Once you’re live, operations are about consistency: sending clean data on time, checking tracking and exception reports, and working with us on any issues. We’ll provide access to tracking and reporting so you can run your side of the process. If your volume or workflow changes, we can adjust cut-offs or integration approach — the goal is a setup that’s sustainable for both sides.",
      },
    ],
    industrySlugs: ["coffee-roasters", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "niagara"],
    relatedClusterSlugs: ["csv-delivery-uploads", "api-order-ingestion"],
    extraLinks: [
      { path: "onboarding", label: "Merchant onboarding" },
      { path: "integrations", label: "Integrations" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
];

export function getIntegrationsEducationBySlug(slug: string): IntegrationsEducationPage | null {
  return INTEGRATIONS_EDUCATION_PAGES.find((p) => p.slug === slug) ?? null;
}

export function getAllIntegrationsEducationSlugs(): string[] {
  return INTEGRATIONS_EDUCATION_PAGES.map((p) => p.slug);
}

const EXTRA_PATH_BUILDER: Record<string, (locale: Locale) => string> = {
  onboarding: business,
  integrations: integrations,
  serviceAreas: serviceAreas,
};

export function buildIntegrationsEducationInternalLinks(
  locale: Locale,
  page: IntegrationsEducationPage,
  slugBuilder: (locale: Locale, s: string) => string
): {
  industry: IntegrationsEducationLink[];
  serviceAreas: IntegrationsEducationLink[];
  extra: IntegrationsEducationLink[];
  cluster: IntegrationsEducationLink[];
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
      const p = getIntegrationsEducationBySlug(s);
      return p ? { href: slugBuilder(locale, s), label: p.title } : null;
    })
    .filter(Boolean) as IntegrationsEducationLink[];

  return { industry, serviceAreas: serviceAreasLinks, extra, cluster };
}
