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
  {
    slug: "sms-status-notifications",
    title: "SMS status notifications",
    description:
      "How PorterChain uses SMS for delivery status and exception alerts — operational notifications tied to capacity runs, not a marketing channel product.",
    intro:
      "SMS keeps receivers and ops aligned when a run is en route, delayed, or needs a quick confirmation. PorterChain uses SMS as part of capacity execution — status and exceptions on live shipments — not as a standalone messaging SKU.",
    sections: [
      {
        heading: "What SMS is for",
        body: "Typical uses: shareable status prompts, ETA updates when a window slips, and exception alerts when access fails or a customer is not available. Messages point back to tracking and the shipment record so everyone works from one story.",
      },
      {
        heading: "Tied to the capacity run",
        body: "Notifications follow the vehicle-and-driver assignment that is actually executing. When ops reassigns capacity, status can update with the same shipment — not a disconnected text thread that ops never sees.",
      },
      {
        heading: "What we do not promise",
        body: "We do not sell SMS marketing campaigns or guarantee delivery of every carrier message in every region. Notification options are confirmed during onboarding for your program tier and channels.",
      },
    ],
    industrySlugs: ["ecommerce", "pharmacy-medical", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: [
      "email-status-notifications",
      "whatsapp-status-notifications",
      "webhooks-delivery-events",
    ],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Get a quote" },
    ],
  },
  {
    slug: "email-status-notifications",
    title: "Email status notifications",
    description:
      "Email alerts for GTA delivery status, exceptions, and proof closeout — operational messages aligned to PorterChain capacity runs.",
    intro:
      "Email is the default audit trail for many B2B teams. PorterChain can send status and exception notices by email so dispatch, sales, and receivers stay aligned without calling the control tower for every ETA.",
    sections: [
      {
        heading: "Status and exception mail",
        body: "Use email for pickup confirmation, en-route updates, failed-stop reasons, and proof-of-delivery summaries. Keep the shipment reference in the subject or body so finance and ops can find the record later.",
      },
      {
        heading: "Works with CSV and API intake",
        body: "Whether you submit by CSV, API, or admin-assisted intake, email notifications can still attach to the created run. Channel choice is independent of how orders enter the system.",
      },
      {
        heading: "Boundaries",
        body: "Email is best-effort operational messaging — not a guaranteed SLA for mailbox delivery, and not a substitute for live tracking when a receiver needs minute-level ETA.",
      },
    ],
    industrySlugs: ["electrical-distribution", "coffee-roasters", "ecommerce"],
    serviceAreaSlugs: ["toronto", "mississauga", "hamilton"],
    relatedClusterSlugs: [
      "sms-status-notifications",
      "whatsapp-status-notifications",
      "csv-delivery-uploads",
    ],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Get a quote" },
    ],
  },
  {
    slug: "whatsapp-status-notifications",
    title: "WhatsApp status notifications",
    description:
      "WhatsApp updates for delivery status and receiver coordination on PorterChain GTA capacity runs — ops messaging, not a chatbots SKU.",
    intro:
      "Some receivers and field teams prefer WhatsApp for quick status. PorterChain can use WhatsApp as an operational channel for tracking prompts and exception coordination where enabled for your program — always tied back to the shipment record.",
    sections: [
      {
        heading: "When WhatsApp helps",
        body: "Useful for contractors, clinic staff, and small B2B receivers who already live in WhatsApp. A short status prompt with a tracking link beats a phone tag loop with dispatch.",
      },
      {
        heading: "Still one source of truth",
        body: "WhatsApp messages should not become a shadow ticket system. Exceptions and proof still live with the shipment so finance and ops share the same closeout.",
      },
      {
        heading: "Availability",
        body: "WhatsApp options depend on program configuration and regional messaging rules. We confirm what is enabled during onboarding rather than promising every template for every account.",
      },
    ],
    industrySlugs: ["construction-materials", "pharmacy-medical", "cosmetics"],
    serviceAreaSlugs: ["toronto", "vaughan", "markham"],
    relatedClusterSlugs: [
      "sms-status-notifications",
      "email-status-notifications",
      "operational-setup-merchants",
    ],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Get a quote" },
    ],
  },
  {
    slug: "webhooks-delivery-events",
    title: "Webhooks and delivery events",
    description:
      "Outbound webhooks for PorterChain delivery events — status, exceptions, and proof signals your systems can consume.",
    intro:
      "When your WMS, OMS, or internal tools need machine-readable updates, webhooks push delivery events as the capacity run progresses. This page outlines the practical model — full schemas and signing live in developer docs.",
    sections: [
      {
        heading: "What events are for",
        body: "Typical signals: shipment created, en route, delivered, failed with reason, and proof available. Your system updates order status without polling a dashboard.",
      },
      {
        heading: "Security and retries",
        body: "Production webhooks use signed payloads and retry behavior documented for partners. We confirm endpoint requirements during technical onboarding.",
      },
      {
        heading: "Start with docs, finish with a quote path",
        body: "Read the partner API and webhook guides on Developers for schemas. Commercial capacity and cut-offs still start with a written quote — webhooks do not replace vehicle-and-driver coverage.",
      },
    ],
    industrySlugs: ["ecommerce", "coffee-roasters", "electrical-distribution"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: [
      "api-order-ingestion",
      "sms-status-notifications",
      "email-status-notifications",
    ],
    extraLinks: [
      { path: "integrations", label: "Integrations" },
      { path: "onboarding", label: "Get a quote" },
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
