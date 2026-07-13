/**
 * Reusable FAQ cluster framework for Porterchain SEO.
 * Each cluster has a slug, title, description, intro, FAQ items, and link targets
 * for industry and city pages so every FAQ page is useful and internally linked.
 * All CTAs point to the existing merchant wizard only.
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

export type FAQItem = { question: string; answer: string };

export type FAQCluster = {
  slug: string;
  title: string;
  description: string;
  /** Intro paragraph(s) for a non-thin page. */
  intro: string;
  items: FAQItem[];
  /** Industry slugs to link to (industry/[slug]). */
  industrySlugs: string[];
  /** Service area slugs to link to (service-areas/[slug]). */
  serviceAreaSlugs: string[];
  /** Optional extra links (e.g. onboarding, integrations, pricing). */
  extraLinks?: {
    path: "onboarding" | "integrations" | "pricing" | "serviceAreas";
    label: string;
  }[];
};

export type FAQClusterLink = { href: string; label: string };

/** Construction + legacy niches for FAQ and cluster internal links. */
export const PRIMARY_INDUSTRY_SLUGS = [
  "construction-materials",
  "electrical-distribution",
  "plumbing-supply",
  "coffee-roasters",
  "pharmacy-medical",
  "cosmetics",
] as const;

/** All FAQ clusters. Content is substantive so pages are non-thin. */
export const FAQ_CLUSTERS: FAQCluster[] = [
  {
    slug: "construction-delivery",
    title: "Construction material delivery: jobsite and distributor FAQ",
    description:
      "FAQ on construction material delivery in Ontario — jobsite drops, pallet freight, proof of delivery, and recurring routes for distributors and contractors.",
    intro:
      "Building supply distributors and contractors need delivery that respects jobsite windows, handles palletized freight, and provides proof of delivery for every drop. Porterchain runs recurring and same-day routes across the GTA and Ontario with vans, pickups, and box trucks matched to your materials. Below are common questions about construction material delivery.",
    items: [
      {
        question: "Do you deliver construction materials to job sites?",
        answer:
          "Yes. We deliver lumber, drywall, steel, aggregates, and general building materials to job sites and trade customers. Share your typical routes, site access notes, and time windows and we align capacity and vehicles.",
      },
      {
        question: "What vehicles do you use for construction freight?",
        answer:
          "Pickups and cargo vans for smaller runs; 16 ft box trucks for palletized materials and larger loads. We match the vehicle to weight, dimensions, and site access.",
      },
      {
        question: "Do you provide proof of delivery for jobsite drops?",
        answer:
          "Every shipment includes photo proof, digital signatures where required, and a tracking link. You and your site teams get clear status and ETA in real time.",
      },
      {
        question: "Which areas do you serve for construction delivery?",
        answer:
          "We serve the GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, London, Niagara, Oshawa, and surrounding Ontario regions.",
      },
    ],
    industrySlugs: ["construction-materials", "electrical-distribution", "plumbing-supply"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "hamilton", "kitchener-waterloo"],
    extraLinks: [
      { path: "serviceAreas", label: "Service areas" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "electrical-distributor-delivery",
    title: "Electrical distributor delivery: wholesale and contractor FAQ",
    description:
      "FAQ on delivery for electrical wholesalers and distributors — same-day cutoffs, wire and panel runs, and recurring routes across Ontario.",
    intro:
      "Electrical distributors and wholesalers need reliable last-mile delivery to contractors, job sites, and counter pickup accounts. Porterchain runs recurring routes and same-day capacity with tracking on every shipment. Here are common questions about electrical distribution delivery.",
    items: [
      {
        question: "Do you deliver for electrical wholesalers and distributors?",
        answer:
          "Yes. We partner with electrical distributors for recurring delivery to contractors, job sites, and trade accounts. Share your volume, zones, and cut-off times and we align local capacity.",
      },
      {
        question: "Can you handle same-day runs for electrical supply?",
        answer:
          "Same-day delivery is available in our service areas subject to cut-off times and capacity. We work with you on time windows so contractors get materials when the job needs them.",
      },
      {
        question: "How do contractors track their delivery?",
        answer:
          "Every shipment gets a tracking link with live status and ETA. Share it with contractors or site contacts so they know when materials arrive.",
      },
      {
        question: "Which cities do you cover for electrical delivery?",
        answer:
          "We operate across the GTA, Hamilton, Kitchener-Waterloo, London, Niagara, and other Ontario regions. Check our electrical distribution industry page and service area pages for your city.",
      },
    ],
    industrySlugs: ["electrical-distribution", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "hamilton", "kitchener-waterloo"],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  {
    slug: "plumbing-supply-delivery",
    title: "Plumbing supply delivery: wholesaler and contractor FAQ",
    description:
      "FAQ on plumbing supply delivery — pipe, fixtures, and wholesale runs for plumbing distributors across Ontario.",
    intro:
      "Plumbing supply houses and wholesalers need predictable delivery to contractors, renovators, and commercial sites. Porterchain runs recurring routes with vans and trucks sized for pipe, fixtures, and palletized stock. Here are common questions about plumbing supply delivery.",
    items: [
      {
        question: "Do you deliver for plumbing wholesalers?",
        answer:
          "Yes. We support plumbing supply distributors with recurring delivery to contractors and trade accounts. Tell us your routes, volume, and time windows and we align capacity.",
      },
      {
        question: "What can you carry for plumbing supply runs?",
        answer:
          "Vans and box trucks for pipe, fixtures, fittings, and palletized stock. Share weight and dimensions for specialty runs and we match the right vehicle.",
      },
      {
        question: "Can we run recurring routes to the same contractors?",
        answer:
          "Yes. Recurring routes are a core use case. We align drivers and vehicles to your weekly or daily patterns with consistent ETAs and tracking.",
      },
      {
        question: "Where do you deliver plumbing supply?",
        answer:
          "Across the GTA, Toronto, Mississauga, Brampton, Vaughan, Hamilton, Kitchener-Waterloo, and other Ontario service areas. Contact us with your zones to confirm coverage.",
      },
    ],
    industrySlugs: ["plumbing-supply", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "hamilton", "kitchener-waterloo"],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  {
    slug: "delivery-pricing",
    title: "Delivery pricing: how merchant delivery is priced",
    description:
      "How Porterchain prices recurring and same-day delivery for merchants. Stop-based, zone-based, and volume pricing.",
    intro:
      "Porterchain prices B2B delivery capacity — not software seats. Pricing is quote-based on vehicle class, distance, stops, urgency (same-day vs scheduled), and handling. Recurring routes and fleet overflow use the same model: predictable cost aligned to your lanes without hidden platform fees. Share your stops, zones, and freight profile and we confirm numbers in writing before dispatch.",
    items: [
      {
        question: "How is delivery pricing structured?",
        answer:
          "Quote-based on vehicle class, distance, stops, urgency (same-day vs scheduled), and handling. Recurring routes often use per-stop or per-route rates; same-day runs factor zone and cut-off time. We confirm pricing in writing after understanding your volume and service areas — no hidden platform fees.",
      },
      {
        question: "Is there a minimum volume or commitment?",
        answer:
          "We work with merchants who have recurring or regular delivery needs. Minimums and commitment terms are discussed during onboarding so they fit your volume. There is no long-term lock-in before we've confirmed fit and pricing.",
      },
      {
        question: "Do you offer pricing for different industries?",
        answer:
          "Yes. Pricing can vary by industry and use case (e.g. wholesale vs. subscription, pharmacy vs. retail) because volume patterns and requirements differ. We tailor pricing to your workflow and service areas.",
      },
      {
        question: "Where can I see pricing for my area?",
        answer:
          "We deliver across the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, and other Ontario regions. Contact us with your volume and service areas and we'll provide pricing for your zones.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "onboarding",
    title: "Merchant onboarding: how to get started",
    description:
      "How Porterchain onboarding works for new merchants. Steps, timeline, and what to expect.",
    intro:
      "Getting started with Porterchain is designed to be fast. We focus on your volume, service areas, and workflow so we can align capacity and agree on SLAs without long forms. Here are the most common questions about onboarding.",
    items: [
      {
        question: "How long does onboarding take?",
        answer:
          "Most merchants are set up within days, not weeks. We confirm coverage for your service areas, align capacity to your routes, and get you access to tracking and reporting. Complex integrations (e.g. API) may take longer and we'll outline that upfront.",
      },
      {
        question: "What do I need to provide to get started?",
        answer:
          "We need your volume (e.g. stops per week), service areas or delivery zones, and any time windows or special requirements. You can start with spreadsheets or email; we'll guide you through the details. No need for a full integration on day one.",
      },
      {
        question: "Is there a contract or commitment?",
        answer:
          "We confirm fit and pricing before any commitment. Terms are discussed during onboarding. Our goal is to get you live quickly so you can see how delivery runs with one partner.",
      },
      {
        question: "Can I get started in my city?",
        answer:
          "We operate in the GTA, Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington, Oshawa, Kitchener-Waterloo, London, St. Catharines, and Niagara. If you're in one of these areas, we can typically get you started.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [{ path: "onboarding", label: "How onboarding works" }],
  },
  {
    slug: "csv-uploads",
    title: "CSV uploads and bulk orders",
    description: "How to use CSV uploads for bulk or recurring orders with Porterchain.",
    intro:
      "Many merchants manage orders or stops in spreadsheets. We support CSV uploads so you can send us runs without building an integration first. Below are answers to common questions about CSV and bulk orders.",
    items: [
      {
        question: "Do you support CSV uploads for orders?",
        answer:
          "Yes. You can submit orders or stops via CSV so we can run your routes. This is useful for recurring runs (e.g. weekly café drops) or one-off bulk orders. We'll confirm the format and required columns during onboarding.",
      },
      {
        question: "What format should the CSV be in?",
        answer:
          "We provide a template or specification that includes address, contact, time window, and any reference fields. Once you're set up, you can reuse the same format for recurring uploads.",
      },
      {
        question: "Can I move from CSV to API later?",
        answer:
          "Yes. Many merchants start with CSV or email and move to API when they're ready. We'll help you transition so your workflow stays consistent.",
      },
      {
        question: "Which industries use CSV uploads?",
        answer:
          "Coffee roasters, pharmacies, beauty brands, and other merchants with recurring routes often use CSV or spreadsheets. If you're in one of these verticals, we can set up CSV-based ordering for your service areas.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    extraLinks: [{ path: "onboarding", label: "How onboarding works" }],
  },
  {
    slug: "api-integrations",
    title: "API and integrations for delivery",
    description: "How to integrate with Porterchain via API and what integrations we support.",
    intro:
      "Porterchain offers API access for merchants who want to push orders, pull tracking, and automate delivery from their systems. We also support common workflows so you can scale without building everything from scratch. Here are answers to common integration questions.",
    items: [
      {
        question: "Do you have an API for orders and tracking?",
        answer:
          "Yes. Our API supports order creation, status updates, and tracking so you can integrate delivery into your e-commerce, ERP, or operations tools. We'll provide documentation and support during integration.",
      },
      {
        question: "What can I integrate with?",
        answer:
          "You can integrate with your own systems via API. We work with merchants on e-commerce platforms, subscription systems, and internal tools. If you have a specific stack, we can outline how it would connect.",
      },
      {
        question: "How long does API integration take?",
        answer:
          "It depends on your system and requirements. We'll scope the integration and timeline during onboarding. Many merchants start with CSV or manual entry and add API when they're ready.",
      },
      {
        question: "Is the API available in all service areas?",
        answer:
          "Yes. API access is available for all our service areas (GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, and others). Coverage is the same whether you use API, CSV, or another method.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "kitchener-waterloo", "london"],
    extraLinks: [{ path: "integrations", label: "Integrations" }],
  },
  {
    slug: "local-service-areas",
    title: "Local service areas: where we deliver",
    description:
      "Porterchain delivery coverage: GTA, Toronto, Mississauga, Kitchener-Waterloo, London, Niagara, Oshawa, and more.",
    intro:
      "We run recurring and same-day delivery in defined local service areas across Ontario. Each region has dedicated coverage so merchants get consistent, reliable delivery. Below we answer questions about where we deliver and how to confirm coverage for your area.",
    items: [
      {
        question: "Which cities and regions do you serve?",
        answer:
          "We serve the Greater Toronto Area (Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington), Oshawa and Durham, Kitchener-Waterloo, London, St. Catharines, and the Niagara region. Each area has a dedicated page with delivery details.",
      },
      {
        question: "How do I know if you deliver to my address?",
        answer:
          "Check our service area pages for your city or region. If you're in a listed area, we can typically serve you. Contact us with your address or postal code and we'll confirm coverage and next steps.",
      },
      {
        question: "Do you deliver outside the GTA?",
        answer:
          "Yes. We deliver in Kitchener-Waterloo, London, Niagara, St. Catharines, Oshawa, and other Ontario regions. Coverage is expanding; see our service areas hub for the full list.",
      },
      {
        question: "Is same-day delivery available in my area?",
        answer:
          "Same-day delivery is available in our service areas subject to cut-off times and capacity. Check the service area page for your city for details, or contact us with your typical volume and zones.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: [
      "toronto",
      "mississauga",
      "brampton",
      "kitchener-waterloo",
      "london",
      "oshawa",
      "st-catharines",
      "niagara",
    ],
    extraLinks: [{ path: "serviceAreas", label: "View all service areas" }],
  },
  {
    slug: "pharmacy-delivery",
    title: "Pharmacy delivery: compliance and patient delivery",
    description:
      "FAQ on pharmacy and prescription delivery: compliance, chain of custody, and service areas.",
    intro:
      "Porterchain supports pharmacy and patient delivery with tracking and chain-of-custody visibility. We work with community pharmacies and clinics that need reliable, compliant delivery. Here are common questions about pharmacy delivery.",
    items: [
      {
        question: "Do you handle prescription delivery?",
        answer:
          "Yes. We work with pharmacies on prescription and patient delivery. Routes are set up with appropriate handling and tracking so you have visibility from pickup to delivery.",
      },
      {
        question: "How is chain of custody and compliance handled?",
        answer:
          "We provide full tracking and status visibility for each run. You can see when a shipment was picked up, in transit, and delivered. This supports compliance and audit requirements. Specific compliance needs are discussed during onboarding.",
      },
      {
        question: "Which areas do you serve for pharmacy delivery?",
        answer:
          "We serve the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, St. Catharines, and other Ontario regions. Check the pharmacy delivery page and service area pages for your region.",
      },
      {
        question: "Can you do recurring routes for clinics or patients?",
        answer:
          "Yes. Recurring routes (e.g. weekly patient deliveries or clinic pickups) are a core use case. We align capacity to your schedule and provide consistent time windows where needed.",
      },
    ],
    industrySlugs: ["pharmacy-medical"],
    serviceAreaSlugs: [
      "toronto",
      "mississauga",
      "kitchener-waterloo",
      "london",
      "niagara",
      "oshawa",
    ],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  {
    slug: "coffee-roaster-delivery",
    title: "Coffee roaster delivery: wholesale and café delivery",
    description:
      "FAQ on delivery for coffee roasters: wholesale, cafés, subscription, and same-day.",
    intro:
      "Coffee roasters use Porterchain for wholesale delivery to cafés, subscription boxes, and same-day runs when freshness matters. We run recurring routes and match capacity to your roast cycle. Here are common questions about coffee roaster delivery.",
    items: [
      {
        question: "Do you do wholesale delivery to cafés?",
        answer:
          "Yes. We run recurring wholesale routes to cafés and accounts. You can schedule weekly or bi-weekly drops and we'll handle pickup and delivery with tracking so cafés know when to expect you.",
      },
      {
        question: "What about same-day delivery for fresh roast?",
        answer:
          "Same-day delivery is available in our service areas. We work with you on cut-off times and time windows so you can get fresh roast to key accounts or subscription customers when it matters.",
      },
      {
        question: "Which vehicles do you use for coffee delivery?",
        answer:
          "Sedans and trade vans for smaller wholesale runs; cargo vans and box trucks for multi-stop café and restaurant supply. We match the vehicle to stop count, parcel size, and site access across the GTA.",
      },
      {
        question: "Where do you deliver for roasters?",
        answer:
          "We deliver across the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, and other Ontario regions. See our coffee roaster delivery page and service area pages for your city.",
      },
    ],
    industrySlugs: ["coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  {
    slug: "cosmetics-delivery",
    title: "Cosmetics and beauty brand B2B delivery",
    description:
      "FAQ on wholesale, retail replenishment, and promotional delivery for cosmetics and beauty brands across Ontario.",
    intro:
      "Beauty and cosmetics brands use Porterchain for wholesale counter runs, retail replenishment, and peak promotional capacity — with tracking and proof on every stop. We run recurring routes and same-day overflow when launches or campaigns need extra vehicle capacity. Here are common questions about cosmetics and beauty delivery for Ontario merchants.",
    items: [
      {
        question: "Do you handle wholesale and retail replenishment?",
        answer:
          "Yes. We support B2B delivery to retailers, distributors, and fulfillment partners with recurring pickup and multi-stop routes. Every shipment gets a tracking link with live status and ETA for your ops team and trade customers.",
      },
      {
        question: "Can you do same-day for promotions or launches?",
        answer:
          "Same-day delivery is available in our service areas. We can scale capacity for promotions or launch days when you need extra volume.",
      },
      {
        question: "How do customers track their order?",
        answer:
          "Every shipment gets a tracking link. You can share it with customers so they see live status and ETA. This reduces 'where is my order?' support and builds trust.",
      },
      {
        question: "Which regions do you serve for beauty brands?",
        answer:
          "We serve the GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, and other Ontario regions. Check our cosmetics delivery page and service area pages for your city.",
      },
    ],
    industrySlugs: ["cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  {
    slug: "same-day-delivery",
    title: "Same-day delivery: cut-offs, zones, and reliability",
    description: "FAQ on same-day delivery: how it works, cut-offs, and where it's available.",
    intro:
      "Same-day delivery is available in Porterchain service areas for merchants who need it. We work with you on cut-off times, time windows, and capacity so same-day runs are reliable. Here are common questions.",
    items: [
      {
        question: "How does same-day delivery work?",
        answer:
          "You submit orders or stops by the agreed cut-off time; we run pickup and delivery the same day. Time windows and ETAs are communicated via tracking. Cut-offs and capacity depend on your zone and volume.",
      },
      {
        question: "What are the cut-off times?",
        answer:
          "Cut-offs vary by zone and volume. We'll confirm cut-off times when we set up your account so you know the latest you can submit for same-day delivery.",
      },
      {
        question: "Is same-day available in my city?",
        answer:
          "Same-day delivery is offered in our service areas: GTA, Toronto, Mississauga, Brampton, Kitchener-Waterloo, London, Niagara, Oshawa, St. Catharines, and others. Check the service area page for your city.",
      },
      {
        question: "Can I mix same-day and recurring routes?",
        answer:
          "Yes. Many merchants run recurring routes (e.g. weekly) and use same-day for one-off or peak demand. One partner, one dashboard, so you can manage both from a single place.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: [
      "toronto",
      "mississauga",
      "brampton",
      "kitchener-waterloo",
      "london",
      "niagara",
      "oshawa",
      "st-catharines",
    ],
    extraLinks: [{ path: "serviceAreas", label: "Service areas" }],
  },
  // --- Commercial-intent FAQ pages (query-led) ---
  {
    slug: "how-much-does-local-delivery-cost-toronto",
    title: "How much does local delivery cost in Toronto?",
    description:
      "Local delivery pricing in Toronto and the GTA. How Porterchain prices recurring and same-day delivery for merchants — and how to get a quote.",
    intro:
      "Local delivery cost in Toronto depends on your volume, route type (recurring vs. same-day), and zones. Porterchain typically prices by stops, zones, and volume so you get predictable cost without surprise fees. We don't publish fixed rates because every merchant's pattern is different: weekly café drops, subscription runs, or on-demand same-day all have different economics. To get a clear answer for Toronto (and the GTA), share your typical stops per week and delivery areas — we'll confirm pricing for your setup.",
    items: [
      {
        question: "Is pricing different in Toronto vs. other GTA cities?",
        answer:
          "Pricing can vary by zone within the GTA. Toronto, Mississauga, Brampton, Vaughan, and other areas may have different per-stop or zone rates. We'll give you pricing for the specific areas you serve when you share your volume and routes.",
      },
      {
        question: "What affects the cost of local delivery?",
        answer:
          "Main factors: number of stops per run or per week, whether routes are recurring or same-day, time windows, and vehicle class (sedan through box truck). We align quote-based pricing to these factors so cost is transparent before dispatch.",
      },
      {
        question: "How do I get a quote for Toronto delivery?",
        answer:
          "Contact us with your volume (e.g. stops per week), service areas (Toronto, specific neighbourhoods, or broader GTA), and any time requirements. We'll confirm coverage and provide pricing for your zones — no commitment until we've confirmed fit.",
      },
      {
        question: "Do you deliver elsewhere in Ontario?",
        answer:
          "Yes. We also serve Kitchener-Waterloo, London, Niagara, St. Catharines, Oshawa, and other Ontario regions. Each area has a dedicated service area page with delivery details.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan", "markham"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "how-to-set-up-recurring-deliveries-coffee-roaster",
    title: "How to set up recurring deliveries for a coffee roaster",
    description:
      "Set up recurring delivery for your coffee roastery: wholesale café drops, subscription boxes, and same-day. Steps and what to expect with Porterchain.",
    intro:
      "To set up recurring deliveries for a coffee roaster, you share your volume and routes (e.g. weekly café drops, subscription runs), we confirm coverage for your areas and align capacity, then you're live with one partner and one dashboard. No fleet to run — we handle pickup from your roastery and delivery to cafés or subscribers. You can start with spreadsheets or CSV; we'll confirm the format and get you on recurring routes within days. Same-day options are available when you need them (e.g. launch days or key accounts).",
    items: [
      {
        question: "What do I need to provide to get started?",
        answer:
          "Your typical weekly volume (e.g. number of stops or drops), which areas you deliver to (neighbourhoods, cities), and any time windows (e.g. morning delivery for cafés). You can send a spreadsheet or use our CSV template. We'll confirm capacity and agree on SLAs.",
      },
      {
        question: "Can I do both wholesale and subscription with one partner?",
        answer:
          "Yes. Many roasters run weekly wholesale routes to cafés and separate subscription or D2C runs. Porterchain can handle both so you have one partner and one place to see every run.",
      },
      {
        question: "What about same-day for fresh roast?",
        answer:
          "Same-day delivery is available in our service areas. We'll work with you on cut-off times and time windows so you can get fresh roast to key accounts when it matters.",
      },
      {
        question: "Which areas do you serve for coffee roasters?",
        answer:
          "We deliver across the GTA (Toronto, Mississauga, Brampton, and surrounding), Kitchener-Waterloo, London, Niagara, Oshawa, and other Ontario regions. See our coffee roaster delivery page and service area pages for your city.",
      },
    ],
    industrySlugs: ["coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "how-pharmacy-courier-delivery-works-gta",
    title: "How pharmacy courier delivery works in the GTA",
    description:
      "How Porterchain runs pharmacy and patient delivery in the GTA: compliance, tracking, recurring routes, and service areas.",
    intro:
      "Pharmacy courier delivery in the GTA with Porterchain works like this: you share your delivery needs (e.g. patient deliveries, clinic pickups, recurring routes), we confirm coverage for Toronto, Mississauga, Brampton, and other GTA areas and set up routes with full tracking and chain-of-custody visibility. We run the fleet and last mile; you get one dashboard for status and ETAs so you and your patients know when to expect delivery. Recurring and same-day options are available. Compliance and handling requirements are discussed during onboarding so we meet your standards.",
    items: [
      {
        question: "How is tracking and chain of custody handled?",
        answer:
          "Every run has full tracking from pickup to delivery. You can see status and ETA in your dashboard, and we maintain visibility so you have an audit trail. Specific compliance or documentation needs are discussed during onboarding.",
      },
      {
        question: "Can you do recurring routes for patients or clinics?",
        answer:
          "Yes. Recurring routes (e.g. daily or weekly patient deliveries, clinic pickups) are a core use case. We align capacity to your schedule and provide consistent time windows where needed.",
      },
      {
        question: "Which GTA areas do you serve for pharmacy delivery?",
        answer:
          "We serve Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Burlington, Oshawa, and the broader GTA. Each area has a dedicated service area page. We also serve Kitchener-Waterloo, London, and Niagara.",
      },
      {
        question: "How do I get started with pharmacy delivery?",
        answer:
          "Contact us with your volume, service areas, and any compliance or time-window requirements. We'll confirm coverage and walk you through onboarding. No long-term commitment until we've confirmed fit and pricing.",
      },
    ],
    industrySlugs: ["pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan", "markham", "oshawa"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "how-to-onboard-merchant-csv-upload",
    title: "How to onboard a merchant with CSV upload",
    description:
      "Onboard merchants using CSV upload: format, process, and moving to API later. Porterchain supports CSV for bulk and recurring orders.",
    intro:
      "To onboard a merchant with CSV upload, we first confirm their service areas and volume. Then we provide a CSV template or specification (address, contact, time window, reference fields) so they can submit orders or stops without an integration. They upload the file (or send it by email) and we run the route. Onboarding typically takes days, not weeks. Many merchants start with CSV and move to API when they're ready — we support that transition so their workflow stays consistent.",
    items: [
      {
        question: "What columns or format does the CSV need?",
        answer:
          "We provide a template that includes the required fields: delivery address, contact, and any time window or reference ID. We'll confirm the exact format during onboarding so it fits your existing process (e.g. export from your system).",
      },
      {
        question: "Can merchants use CSV for recurring routes?",
        answer:
          "Yes. Recurring routes (e.g. weekly café drops) are often run from a CSV that's updated each cycle. You send the file; we run the route and provide tracking. Same format can be reused each time.",
      },
      {
        question: "What if they want to switch to API later?",
        answer:
          "We support the move from CSV to API. Many merchants start with CSV or email and add API when they're ready to automate. We'll help with the transition so there's no disruption to delivery.",
      },
      {
        question: "Which industries use CSV upload?",
        answer:
          "Coffee roasters, pharmacies, beauty brands, and other merchants with recurring or bulk orders often use CSV. If you're in one of these verticals, we can set up CSV-based ordering for your service areas.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "integrations", label: "Integrations" },
    ],
  },
  {
    slug: "what-vehicle-right-for-parcel-volume",
    title: "What vehicle is right for my parcel volume?",
    description:
      "Choose the right vehicle for your B2B freight: sedans through box trucks. How Porterchain matches vehicle-and-driver capacity to your routes.",
    intro:
      "The right vehicle for your B2B freight depends on stop count, parcel size, and site access. Porterchain matches vehicle-and-driver capacity to the run: sedans and SUVs for documents and small parcels, trade vans and cargo vans for multi-stop wholesale, pickups and box trucks for palletized or jobsite freight. You do not manage fleet — we assign capacity from your volume and route profile. Share typical stops per week and what you move (wire, prescriptions, building materials, retail cartons) and we align the right vehicle class.",
    items: [
      {
        question: "Do I choose the vehicle or does Porterchain?",
        answer:
          "We match vehicle class to your run based on volume, freight profile, and route density. You share what you are moving and how many stops; we assign sedans, vans, pickups, or box trucks as appropriate. Site access and pallet weight are factored in before dispatch.",
      },
      {
        question: "What if my volume grows or changes?",
        answer:
          "Capacity can scale with your volume. If you add stops or expand zones, we'll adjust the vehicle mix and capacity so your delivery stays reliable without you managing fleet.",
      },
      {
        question: "Are box trucks available for heavier freight?",
        answer:
          "Yes. Pickups and 16–20 ft box trucks are used for palletized materials, construction freight, and bulk wholesale runs across our Ontario service areas. We confirm vehicle fit during onboarding for your lanes.",
      },
      {
        question: "How do I get started with the right vehicle fit?",
        answer:
          "Contact us with your volume (stops per week), parcel type, and service areas. We'll confirm coverage and align the right vehicle and capacity. No commitment until we've confirmed fit and pricing.",
      },
    ],
    industrySlugs: [
      "construction-materials",
      "electrical-distribution",
      "plumbing-supply",
      "coffee-roasters",
      "pharmacy-medical",
      "cosmetics",
    ],
    serviceAreaSlugs: ["toronto", "mississauga", "kitchener-waterloo", "london", "niagara"],
    extraLinks: [
      { path: "onboarding", label: "How onboarding works" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "same-day-retail-distribution",
    title: "Same-day retail distribution: store replenishment FAQ",
    description:
      "FAQ on same-day retail distribution and store replenishment in the GTA — multi-stop routes, cut-offs, and fleet overflow for retailers and wholesalers.",
    intro:
      "Retailers and wholesale distributors need same-day store replenishment when DC trucks are full, a promo hits, or a store is out of stock. Porterchain provides vehicle-and-driver capacity for multi-stop retail distribution across the GTA — sedans through box trucks with tracking and proof on every stop. Below are common questions about same-day retail distribution.",
    items: [
      {
        question: "Who can deliver store replenishment right now near me in Toronto?",
        answer:
          "Porterchain provides same-day vehicle-and-driver capacity for retail store replenishment across the GTA. If you need multi-stop runs or palletized freight today near Toronto, Mississauga, or Brampton, request a quote with your store list — we confirm capacity within one business day and dispatch sedan through box truck with live tracking and proof on every stop.",
      },
      {
        question: "Do you handle same-day retail store replenishment?",
        answer:
          "Yes. We run same-day multi-stop distribution for retailers, brand partners, and wholesalers subject to cut-off times and capacity. Share your stores, SKUs, and time windows and we align vehicles and drivers.",
      },
      {
        question: "Can you cover fleet overflow when our trucks are booked?",
        answer:
          "Fleet overflow is a core use case. When your fleet is at capacity or a driver is out, we dispatch matched vehicle-and-driver capacity — often same day — with live tracking and proof of delivery.",
      },
      {
        question: "What vehicles do you use for retail distribution?",
        answer:
          "Sedans and trade vans for small parcel runs; cargo vans and box trucks for multi-stop replenishment and palletized freight. We match vehicle class to stop count, dock access, and freight profile.",
      },
      {
        question: "Which areas do you serve for retail distribution?",
        answer:
          "We serve the GTA — Toronto, Mississauga, Brampton, Vaughan, Markham, Oakville, Hamilton — and Kitchener-Waterloo, London, Niagara, and Oshawa. Request a quote with your store list and zones.",
      },
    ],
    industrySlugs: ["cosmetics", "coffee-roasters", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan", "markham"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "fleet-overflow-wholesale-delivery",
    title: "Fleet overflow wholesale delivery FAQ",
    description:
      "FAQ on fleet overflow and backup capacity for wholesale distributors — electrical, plumbing, construction, and industrial supply across Ontario.",
    intro:
      "Wholesale distributors hit fleet overflow when every truck is booked, a driver calls out, or peak season exceeds in-house capacity. Porterchain provides backup vehicle-and-driver capacity for counter-to-jobsite and depot-to-customer runs — same-day urgent and recurring overflow lanes with tracking and proof. Here are common questions about fleet overflow for wholesale delivery.",
    items: [
      {
        question: "Who can deliver a 50kg pallet right now near me?",
        answer:
          "Porterchain dispatches matched vehicle-and-driver capacity for palletized B2B freight across the GTA — cargo vans and box trucks for loads from small pallet to full truckload. Share pickup location, weight, and delivery window on a quote request; same-day overflow capacity is subject to cut-off times and availability in your zone.",
      },
      {
        question: "What is fleet overflow delivery?",
        answer:
          "Fleet overflow is backup vehicle-and-driver capacity when your own fleet cannot cover a shipment — driver out, peak demand, or an extra jobsite drop. We dispatch matched capacity, often same day, without you hiring drivers or buying trucks.",
      },
      {
        question: "Do you work with electrical and plumbing wholesalers?",
        answer:
          "Yes. We partner with electrical, plumbing, and building supply distributors for overflow runs from counter to contractor or jobsite. Share cut-offs, freight profile, and zones and we align vans or box trucks.",
      },
      {
        question: "How quickly can you dispatch overflow capacity?",
        answer:
          "Same-day overflow is available in our service areas subject to cut-off times and vehicle class. Emergency and urgent runs are a core service — request a quote and we confirm the window in writing.",
      },
      {
        question: "How does pricing work for overflow lanes?",
        answer:
          "Quote-based on vehicle class, distance, stops, and urgency. No platform fees — we confirm pricing in writing before dispatch so overflow lanes stay predictable alongside your in-house fleet costs.",
      },
    ],
    industrySlugs: ["electrical-distribution", "plumbing-supply", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "hamilton", "kitchener-waterloo"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "onboarding", label: "How onboarding works" },
    ],
  },
];

const slugSet = new Set(FAQ_CLUSTERS.map((c) => c.slug));

export function getFaqClusterBySlug(slug: string): FAQCluster | null {
  return FAQ_CLUSTERS.find((c) => c.slug === slug) ?? null;
}

export function getAllFaqClusterSlugs(): string[] {
  return FAQ_CLUSTERS.map((c) => c.slug);
}

export function buildFaqClusterInternalLinks(
  locale: Locale,
  cluster: FAQCluster
): { industry: FAQClusterLink[]; serviceAreas: FAQClusterLink[]; extra: FAQClusterLink[] } {
  const industry = cluster.industrySlugs.map((s) => ({
    href: industrySlug(locale, s),
    label: INDUSTRY_PAGE_LABELS[s] ?? s.replace(/-/g, " "),
  }));

  const serviceAreaLinks = cluster.serviceAreaSlugs.map((s) => ({
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
    cluster.extraLinks?.map((e) => ({
      href: pathToHref[e.path] ?? "#",
      label: e.label,
    })) ?? [];

  return { industry, serviceAreas: serviceAreaLinks, extra };
}
