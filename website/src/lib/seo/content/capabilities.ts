/**
 * Capability spokes for PorterChain — full-stack capacity outcomes
 * (vehicles + drivers + ops + software), not software-seat features.
 */

import type { Locale } from "@/i18n/routing";
import { industrySlug, serviceAreaSlug, business, platform, serviceAreas } from "../routes";
import { INDUSTRY_PAGE_LABELS } from "../internal-linking";

export type CapabilitySection = {
  heading: string;
  body: string;
};

export type CapabilityPage = {
  slug: string;
  title: string;
  description: string;
  intro: string;
  sections: CapabilitySection[];
  industrySlugs: string[];
  serviceAreaSlugs: string[];
  relatedClusterSlugs?: string[];
  extraLinks?: {
    path: "onboarding" | "platform" | "serviceAreas" | "trustClaims";
    label: string;
  }[];
};

export type CapabilityLink = { href: string; label: string };

export const CAPABILITY_PAGES: CapabilityPage[] = [
  {
    slug: "multi-stop-delivery",
    title: "Multi-stop delivery capacity",
    description:
      "Multi-stop B2B delivery capacity in the GTA — wholesale loops, clinic runs, and warehouse waves with the right vehicle and proof on every stop.",
    intro:
      "Multi-stop delivery is a capacity problem: denser routes, the right vehicle class, and drivers who can execute windows without turning every stop into a phone call. PorterChain runs multi-drop lanes with tracking and proof so wholesale, clinic, and warehouse teams keep cut-offs.",
    sections: [
      {
        heading: "Built for B2B loops, not single parcel drops",
        body: "Wholesale counters, clinic supply, and 3PL outbound rarely ship one stop. We sequence multi-stop runs across Toronto, Peel, and York with vehicle fit for cartons, totes, long stock, or light pallets — and shareable status for every receiver on the loop.",
      },
      {
        heading: "Cut-offs and staging that ops can trust",
        body: "Multi-stop fails when freight is not ready or windows were never confirmed. We align cut-offs by zone, require access notes where needed, and keep exception reasons with the order so the next wave does not repeat the same miss.",
      },
      {
        heading: "Proof that closes the loop",
        body: "Photo, signature, and GPS timestamps on each stop support billing and customer disputes. Finance and inside sales see the same closeout record your dispatch team uses.",
      },
    ],
    industrySlugs: ["ecommerce", "electrical-distribution", "pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: ["recurring-routes", "exception-recovery", "multi-location-routing"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "platform", label: "How we operate" },
    ],
  },
  {
    slug: "recurring-routes",
    title: "Recurring route capacity",
    description:
      "Recurring GTA delivery lanes — weekly wholesale, café, and clinic programs with vehicle-and-driver capacity, tracking, and proof.",
    intro:
      "Recurring routes turn delivery from a scramble into a program: fixed days, known windows, and capacity reserved for your lanes. PorterChain supplies the vehicles and drivers behind those templates — with the same tracking and proof standards every week.",
    sections: [
      {
        heading: "Capacity programs, not one-off roulette",
        body: "We align vehicle class and driver coverage to your weekly pattern — café drops, counter-to-jobsite wholesale, clinic replenishment, or warehouse waves. You keep the commercial relationship with your customers; we keep the capacity reliable.",
      },
      {
        heading: "Same-day overflow when the template breaks",
        body: "Peak days, promotions, and truck downtime still happen. Recurring customers can book overflow on the same partner so receivers do not feel a scramble when volume spikes.",
      },
      {
        heading: "Visibility for sales and finance",
        body: "Live tracking and POD on every stop mean inside sales can answer ETA questions and finance can close disputes without chasing drivers.",
      },
    ],
    industrySlugs: ["coffee-roasters", "electrical-distribution", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "markham"],
    relatedClusterSlugs: ["multi-stop-delivery", "branded-tracking", "inventory-transfers"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "branded-tracking",
    title: "Customer tracking and delivery status",
    description:
      "Shareable delivery tracking and ETA for GTA B2B receivers — status your customers can follow without calling dispatch.",
    intro:
      "Receivers expect consumer-grade status on commercial freight. PorterChain provides shareable tracking and ETA so your customers, contractors, and clinic staff see progress — while your team keeps one operational source of truth.",
    sections: [
      {
        heading: "Links your customers can use",
        body: "Share status without forwarding internal tools. Ops, sales, and receivers follow the same shipment story from pickup through proof of delivery.",
      },
      {
        heading: "Tied to capacity, not a disconnected widget",
        body: "Tracking reflects the vehicle-and-driver run that is actually executing. When an exception happens, status and ops notes stay with the shipment instead of vanishing into a text thread.",
      },
      {
        heading: "Proof at closeout",
        body: "When the stop completes, photo and signature records sit with the tracking history — useful for billing, trade disputes, and customer trust.",
      },
    ],
    industrySlugs: ["ecommerce", "construction-materials", "pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "vaughan", "hamilton"],
    relatedClusterSlugs: ["delivery-verification", "exception-recovery"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "trustClaims", label: "Proof & claims" },
    ],
  },
  {
    slug: "exception-recovery",
    title: "Exception recovery and control-tower ops",
    description:
      "How PorterChain recovers stalled GTA deliveries — monitor, reassign capacity, document exceptions, and escalate when a human is needed.",
    intro:
      "Deliveries stall for predictable reasons: closed docks, bad access, wrong vehicle, or customer not available. PorterChain treats recovery as an operations job — control-tower monitoring, capacity reassignment, and documented reasons — not a ticket that waits overnight.",
    sections: [
      {
        heading: "See stalls early",
        body: "Live status surfaces stops that are late or blocked. Ops can intervene before a quiet miss becomes a customer complaint and a redelivery you did not plan for.",
      },
      {
        heading: "Reassign capacity when needed",
        body: "When a unit breaks down or a window slips, we reassign vehicle-and-driver capacity and reset expectations with a documented reason — so sales and receivers are not left guessing.",
      },
      {
        heading: "Document for the next attempt",
        body: "Exception reasons travel with the order. The redelivery brief is accurate, and finance sees why a stop failed instead of arguing from memory.",
      },
    ],
    industrySlugs: ["construction-materials", "pharmacy-medical", "ecommerce"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: ["delivery-verification", "ai-dispatch"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "platform", label: "How we operate" },
    ],
  },
  {
    slug: "ai-dispatch",
    title: "Intelligent matching and dispatch support",
    description:
      "How PorterChain matches vehicle class, driver coverage, and GTA zones — decision support for capacity, not a software-only AI product.",
    intro:
      "Matching the right capacity to a stop is where technology earns its keep: vehicle class, zone coverage, cut-offs, and urgency. PorterChain uses operational intelligence to support dispatch — always with professional drivers and commercial vehicles executing the run.",
    sections: [
      {
        heading: "Match capacity to the freight",
        body: "Sedan through box truck is not a preference quiz. We match class to cube, weight, access, and urgency so the first assignment has a chance to succeed.",
      },
      {
        heading: "Support ops — do not replace accountability",
        body: "Software surfaces options and risks; control-tower ops still owns exceptions and customer commitments. We do not sell an AI seat as the product — capacity that completes is the product.",
      },
      {
        heading: "Grounded in GTA density",
        body: "Matching quality depends on local coverage. Our network focus is Greater Toronto and Ontario metros — realistic ETAs beat national parcel defaults when windows are tight.",
      },
    ],
    industrySlugs: ["electrical-distribution", "construction-materials", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    relatedClusterSlugs: ["exception-recovery", "multi-stop-delivery"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "platform", label: "How we operate" },
    ],
  },
  {
    slug: "delivery-verification",
    title: "Delivery verification and claims-ready proof",
    description:
      "Photo, signature, and GPS proof on every PorterChain stop — closeout records for billing, disputes, and claims follow-up in Ontario.",
    intro:
      "Verification is how capacity becomes trustworthy. Every PorterChain stop can close with photo, signature, and GPS evidence so finance, sales, and customers share one record — and claims start from proof instead of guesswork.",
    sections: [
      {
        heading: "Closeout on every stop",
        body: "Photo and signature POD plus location-stamped completion give receivers and billing teams a shared source of truth.",
      },
      {
        heading: "Exceptions with reasons",
        body: "Failed access, refused freight, or customer not available is documented with the shipment so redelivery and dispute review stay accurate.",
      },
      {
        heading: "Path for loss and damage review",
        body: "When something goes wrong, ops and enterprise contacts work from the same evidence chain. See Trust for insurance and claims process details during vendor review.",
      },
    ],
    industrySlugs: ["construction-materials", "pharmacy-medical", "ecommerce"],
    serviceAreaSlugs: ["toronto", "hamilton", "mississauga"],
    relatedClusterSlugs: ["branded-tracking", "exception-recovery"],
    extraLinks: [
      { path: "trustClaims", label: "Proof & claims" },
      { path: "onboarding", label: "Get a quote" },
    ],
  },
  {
    slug: "multi-location-routing",
    title: "Multi-location capacity routing",
    description:
      "Vehicle-and-driver capacity across multiple GTA branches and warehouses — coordinated pickups, zone-aware matching, and proof on every stop.",
    intro:
      "Multi-location businesses do not fail on software maps — they fail when the wrong branch stages freight, the wrong vehicle shows up, or status lives in three phones. PorterChain supplies capacity across your GTA locations with coordinated pickups, tracking, and proof — not a WMS or inventory SaaS.",
    sections: [
      {
        heading: "Capacity across branches, one partner",
        body: "Counter, warehouse, and store pickups can share one capacity partner. We match vehicle class and windows to the origin that is actually staging the freight — so Mississauga and Vaughan locations do not invent separate courier habits.",
      },
      {
        heading: "Zone-aware execution",
        body: "Toronto, Peel, and York cut-offs differ. Multi-location programs need realistic windows by pickup site, not a single blanket SLA that sales cannot keep.",
      },
      {
        heading: "What this is not",
        body: "We do not replace your inventory system or claim automatic stock balancing across stores. We move staged freight between locations and to customers with drivers, vehicles, and ops recovery.",
      },
    ],
    industrySlugs: ["ecommerce", "electrical-distribution", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan"],
    relatedClusterSlugs: ["inventory-transfers", "multi-stop-delivery", "recurring-routes"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "platform", label: "How we operate" },
    ],
  },
  {
    slug: "inventory-transfers",
    title: "Inventory transfer capacity",
    description:
      "Store-to-store and warehouse-to-store transfer capacity in the GTA — same-day and scheduled moves with tracking and proof, without building transfer fleet.",
    intro:
      "Inventory transfers are capacity runs with two commercial addresses: pull from one dock, deliver to another. PorterChain provides vehicle-and-driver capacity for branch balancing and warehouse replenishment across the GTA — with the same tracking and proof standards as customer deliveries.",
    sections: [
      {
        heading: "Transfers that complete",
        body: "Wrong vehicle class and missing dock contacts kill transfers. We match cargo van through box truck to cube and access, and require the same staging discipline you would use for a customer cut-off.",
      },
      {
        heading: "Same-day and scheduled",
        body: "Use scheduled lanes for weekly replenishment and same-day overflow when a branch is short. One partner keeps both patterns from becoming courier roulette.",
      },
      {
        heading: "Proof for internal accountability",
        body: "Photo and GPS closeout help warehouse and retail ops agree that stock moved — useful when finance or loss-prevention asks what happened to a transfer.",
      },
    ],
    industrySlugs: ["ecommerce", "construction-materials", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    relatedClusterSlugs: ["multi-location-routing", "exception-recovery", "delivery-verification"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "trustClaims", label: "Proof & claims" },
    ],
  },
  {
    slug: "returns-round-trip-capacity",
    title: "Returns and round-trip capacity",
    description:
      "GTA returns and round-trip delivery capacity — pickups, swaps, and two-leg B2B moves with tracking and proof on both ends.",
    intro:
      "Returns and round-trips are capacity problems with two addresses and one commercial promise. PorterChain supplies vehicle-and-driver capacity for pickup-and-return, equipment swaps, and failed-delivery recovery — with tracking and proof so ops can close both legs.",
    sections: [
      {
        heading: "Two legs, one capacity partner",
        body: "Whether you are retrieving unsold stock, swapping display units, or recovering a failed drop, treat both addresses as first-class stops. We match vehicle class to cube and access so the return leg is not an afterthought.",
      },
      {
        heading: "Not a rental or merchandising app",
        body: "This is transportation capacity for B2B returns and round-trips — not a Shopify rental plugin or item-substitution product. You keep the commercial relationship; we execute the move.",
      },
      {
        heading: "Proof on pickup and delivery",
        body: "Photo and GPS closeout on both ends support billing, inventory adjustment, and customer disputes when freight comes back as well as when it goes out.",
      },
    ],
    industrySlugs: ["ecommerce", "construction-materials", "electrical-distribution"],
    serviceAreaSlugs: ["toronto", "mississauga", "vaughan"],
    relatedClusterSlugs: ["exception-recovery", "delivery-verification", "inventory-transfers"],
    extraLinks: [
      { path: "onboarding", label: "Get a quote" },
      { path: "trustClaims", label: "Proof & claims" },
    ],
  },
];

export function getCapabilityBySlug(slug: string): CapabilityPage | null {
  return CAPABILITY_PAGES.find((p) => p.slug === slug) ?? null;
}

export function getAllCapabilitySlugs(): string[] {
  return CAPABILITY_PAGES.map((p) => p.slug);
}

const EXTRA_PATH_BUILDER: Record<
  NonNullable<CapabilityPage["extraLinks"]>[number]["path"],
  (locale: Locale) => string
> = {
  onboarding: business,
  platform,
  serviceAreas,
  trustClaims: (locale) => `/${locale}/trust/claims`,
};

export function buildCapabilityInternalLinks(
  locale: Locale,
  page: CapabilityPage,
  slugBuilder: (locale: Locale, slug: string) => string
): {
  industry: CapabilityLink[];
  serviceAreas: CapabilityLink[];
  extra: CapabilityLink[];
  cluster: CapabilityLink[];
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
      const p = getCapabilityBySlug(s);
      return p ? { href: slugBuilder(locale, s), label: p.title } : null;
    })
    .filter(Boolean) as CapabilityLink[];

  return { industry, serviceAreas: serviceAreasLinks, extra, cluster };
}
