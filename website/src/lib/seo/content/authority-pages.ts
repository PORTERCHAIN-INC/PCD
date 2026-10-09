/**
 * Reusable authority / guides page framework for Porterchain.
 * Educational, practical pages that build trust and reinforce local logistics expertise.
 * All pages are internally linked and support a single CTA to the merchant wizard.
 */

import type { Locale } from "@/i18n/routing";
import { quoteCtaLabel } from "@/lib/cta";
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
  {
    slug: "choose-delivery-vehicle",
    title: "How to choose the right delivery vehicle",
    description:
      "Match cargo van, Sprinter, pickup, or box truck to freight size, site access, and stop count for Ontario B2B delivery.",
    intro:
      "Wrong vehicle class causes failed pickups, wasted capacity cost, or damaged freight. Use freight dimensions, access constraints, and stop density to choose cargo van, Sprinter-class van, pickup, or box truck — then confirm the class in a written quote before dispatch.",
    sections: [
      {
        heading: "Start with freight, not the vehicle name",
        body: "Measure longest piece, total cube, and weight. Palletized freight usually needs a box truck or liftgate-capable capacity. Loose totes and cases often fit a cargo van. Tall racks or long pipe may need Sprinter height or pickup bed length.",
      },
      {
        heading: "Check site access before you lock the class",
        body: "Jobsites, retail docks, and downtown lanes constrain vehicle size. A box truck that cannot turn into the yard fails the stop. When access is tight, prefer cargo or trade van and split pallets across runs if needed.",
      },
      {
        heading: "Confirm class in the quote",
        body: "Tell Porterchain your dimensions, stop count, and time window. We confirm vehicle class and pricing in writing — typically within one business day — so drivers arrive with the right capacity.",
      },
    ],
    industrySlugs: ["construction-materials", "electrical-distribution", "plumbing-supply"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    extraLinks: [
      { path: "pricing", label: "Pricing" },
      { path: "onboarding", label: "Get started" },
    ],
  },
  {
    slug: "prepare-freight-for-pickup",
    title: "How to prepare freight for pickup",
    description:
      "Practical checklist for Ontario shippers — labeling, staging, access notes, and proof requirements before the driver arrives.",
    intro:
      "Most same-day failures start at the dock: freight not ready, unclear labels, or missing site notes. Preparing freight before pickup protects time windows and proof of delivery for billing and customer updates.",
    sections: [
      {
        heading: "Stage and label before the window opens",
        body: "Stage freight in one pickup zone. Label each piece with destination, reference, and piece count. Note fragile or orientation requirements in the order notes — not only on the carton.",
      },
      {
        heading: "Share access and contact details",
        body: "Include gate codes, loading dock hours, forklift availability, and an on-site contact with a phone number. Jobsite deliveries need address clarity so drivers do not idle searching for the drop.",
      },
      {
        heading: "Agree what counts as proof",
        body: "Photo proof, signature, or both — set the requirement when you book. Clear POD standards reduce disputes after delivery.",
      },
    ],
    industrySlugs: ["construction-materials", "coffee-roasters", "pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "mississauga", "vaughan"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "support", label: "Support" },
    ],
  },
  {
    slug: "create-delivery-sop",
    title: "How to create a delivery SOP",
    description:
      "Build a simple delivery standard operating procedure for wholesale, construction, and pharmacy teams using Porterchain capacity.",
    intro:
      "A short SOP keeps inside sales, warehouse, and dispatch aligned when you use overflow or recurring capacity. Document intake, cut-offs, escalation, and proof standards so every run follows the same path.",
    sections: [
      {
        heading: "Define intake and cut-offs",
        body: "Who submits orders, by what time, and in what format (CSV, portal, or API). Publish same-day cut-offs by zone so sales does not promise windows operations cannot hit.",
      },
      {
        heading: "Document exceptions",
        body: "List who to call for failed access, damaged freight, or customer not available. Include Porterchain ops contact and your internal escalation owner.",
      },
      {
        heading: "Close the loop with proof and invoice",
        body: "Require POD review before billing disputes. Keep tracking links with the order record so finance and customers share one source of truth.",
      },
    ],
    industrySlugs: ["electrical-distribution", "plumbing-supply", "pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "hamilton", "kitchener-waterloo"],
    extraLinks: [
      { path: "onboarding", label: "Onboarding" },
      { path: "integrations", label: "Integrations" },
    ],
  },
  {
    slug: "reduce-failed-deliveries",
    title: "How to reduce failed deliveries",
    description:
      "Cut failed B2B deliveries in the GTA — access notes, windows, contacts, and proof standards that prevent redelivery cost.",
    intro:
      "Failed deliveries burn capacity and customer trust. Most failures are preventable: incomplete addresses, closed docks, missing contacts, or freight not ready. Fix the inputs before you add more vehicles.",
    sections: [
      {
        heading: "Validate the stop before dispatch",
        body: "Require a reachable phone, accurate suite or gate, and a delivery window the receiver confirmed. For jobsites, capture GC or site supervisor contact — not only the purchasing office.",
      },
      {
        heading: "Match vehicle and freight to the site",
        body: "Oversized vehicles on tight sites and undersized vehicles for pallets both fail. Confirm class in the quote and stage freight that matches the booked capacity.",
      },
      {
        heading: "Use proof to stop repeat disputes",
        body: "Photo and timestamped POD close loops with receivers and billing. When a stop fails, document the reason so the redelivery brief is accurate.",
      },
    ],
    industrySlugs: ["construction-materials", "coffee-roasters", "cosmetics"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "markham"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "pricing", label: "Pricing" },
    ],
  },
  {
    slug: "evaluate-commercial-courier",
    title: "How to evaluate a commercial courier",
    description:
      "Checklist for Ontario businesses comparing couriers and capacity partners — coverage, vehicles, proof, SLA, and quote process.",
    intro:
      "Choosing a commercial courier is a capacity and accountability decision — not a software tour. Evaluate coverage, vehicle classes, proof standards, escalation, and written quotes against your real lanes.",
    sections: [
      {
        heading: "Coverage and vehicle fit",
        body: "Ask which metros and vehicle classes they run today — cargo van through box truck — and whether they can cover your overflow and recurring lanes with the same partner.",
      },
      {
        heading: "Visibility and proof",
        body: "Require live tracking and photo or signature proof on every stop. If status lives only in a phone call, you will chase exceptions all day.",
      },
      {
        heading: "Commercial clarity",
        body: "Prefer written quotes, clear cut-offs, and documented escalation. Avoid vague platform fees or unnamed subcontracting you cannot explain to customers.",
      },
    ],
    industrySlugs: ["construction-materials", "pharmacy-medical", "electrical-distribution"],
    serviceAreaSlugs: ["toronto", "mississauga", "hamilton"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "support", label: "Contact" },
    ],
  },
  {
    slug: "what-is-a-transportation-capacity-network",
    title: "What is a transportation capacity network?",
    description:
      "How a transportation capacity network differs from courier apps and fleet software — technology plus drivers, vehicles, and ops for GTA B2B delivery.",
    intro:
      "A transportation capacity network sells vehicle-and-driver capacity backed by software and operations — not a software seat, and not a one-off courier roulette. PorterChain runs that model for Ontario businesses: matching, dispatch, tracking, proof, and recovery when a stop goes sideways.",
    sections: [
      {
        heading: "Capacity is the product",
        body: "Customers buy runs that complete: the right vehicle class, a professional driver, a window they can trust, and proof finance can use. Software coordinates the work — it is not the SKU. If the truck never shows, the login does not matter.",
      },
      {
        heading: "Digital and physical together",
        body: "Quotes, booking, live status, and POD live in one system with the people and fleet that execute. That is why overflow, same-day, and recurring lanes can share one partner instead of stitching three vendors.",
      },
      {
        heading: "Built for GTA B2B lanes",
        body: "Wholesale cut-offs, jobsite drops, pharmacy urgency, and warehouse multi-stop all need local density. A network with GTA coverage and ops control beats national parcel defaults when windows and access rules are tight.",
      },
    ],
    industrySlugs: ["electrical-distribution", "construction-materials", "pharmacy-medical"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "onboarding", label: quoteCtaLabel("en") },
    ],
  },
  {
    slug: "same-day-delivery-capacity-gta",
    title: "Same-day delivery capacity in the GTA",
    description:
      "How Ontario businesses use same-day vehicle-and-driver capacity — cut-offs, vehicle fit, tracking, and when overflow beats stretching your own fleet.",
    intro:
      "Same-day in the GTA is a capacity problem: freight ready, the right vehicle free, and a driver who can hit the window. PorterChain supplies that capacity with tracking and proof — as primary coverage or as overflow when your fleet is already booked.",
    sections: [
      {
        heading: "Know your cut-offs by zone",
        body: "Toronto, Peel, and York are not one blanket SLA. Publish realistic same-day cut-offs by pickup zone so sales promises match what ops can execute. Stage freight before the cut-off — late staging is the most common failure.",
      },
      {
        heading: "Match vehicle class to the stop",
        body: "Sedan and cargo van for parcels and totes; trade van and box truck for long stock and pallets. Wrong class burns the window even when the driver is on time. Confirm class in the quote, not at the dock.",
      },
      {
        heading: "Use overflow before you break your fleet",
        body: "When your trucks are full or a unit is down, booked overflow keeps customer promises intact. Share tracking links and POD standards so receivers cannot tell which capacity completed the stop — only that it arrived on time with proof.",
      },
    ],
    industrySlugs: ["ecommerce", "construction-materials", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "markham", "vaughan"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "delivery-failure-modes-and-recovery",
    title: "Delivery failure modes and how ops recovers",
    description:
      "Nine common B2B delivery failure modes in the GTA — and how dispatch, reassignment, and proof close the loop instead of leaving you on hold.",
    intro:
      "Failed stops are usually predictable: bad access notes, closed docks, wrong vehicle, late staging, or no reachable contact. PorterChain treats exceptions as an ops problem — monitor, reassign capacity, document, and escalate — not a ticket that waits overnight.",
    sections: [
      {
        heading: "Failures before the wheels move",
        body: "Incomplete addresses, missing gate codes, freight not ready, and windows the receiver never confirmed. Fix intake: require contact, access notes, and staged freight before dispatch. Most redeliveries start here.",
      },
      {
        heading: "Failures on the road",
        body: "Traffic, vehicle breakdowns, refused freight, and customer not available. Live tracking surfaces stalls early; control-tower ops reassigns capacity or resets the window with a documented reason instead of a silent miss.",
      },
      {
        heading: "Closeout and claims-ready records",
        body: "Photo, signature, and GPS timestamps stop repeat disputes. When a stop fails, the exception reason travels with the order so finance, sales, and the next driver share one brief. That is how recovery scales without tribal knowledge.",
      },
    ],
    industrySlugs: ["electrical-distribution", "pharmacy-medical", "construction-materials"],
    serviceAreaSlugs: ["toronto", "hamilton", "mississauga"],
    extraLinks: [
      { path: "workflow", label: "How delivery works" },
      { path: "support", label: "Contact ops" },
    ],
  },
  {
    slug: "multi-location-capacity-gta",
    title: "Multi-location capacity in the GTA",
    description:
      "How Ontario multi-branch businesses run capacity across counters and warehouses — cut-offs by site, vehicle fit, transfers, and proof.",
    intro:
      "Multi-location delivery is a capacity coordination problem: which site stages freight, which vehicle fits, and who owns status when a stop stalls. PorterChain runs vehicle-and-driver capacity across GTA branches without pretending to be your inventory system.",
    sections: [
      {
        heading: "Name the origin before you promise the window",
        body: "Sales should know which counter or warehouse will stage the run. Wrong-origin pickups burn same-day windows faster than traffic does.",
      },
      {
        heading: "Transfers and customer deliveries share standards",
        body: "Branch balancing and customer drops both need tracking and proof. Using one capacity partner keeps overflow days from inventing a second courier culture.",
      },
      {
        heading: "Cut-offs by zone and site",
        body: "Peel docks and downtown counters are not interchangeable. Publish site-level cut-offs so ops and sales stay aligned.",
      },
    ],
    industrySlugs: ["ecommerce", "electrical-distribution", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
  {
    slug: "inventory-transfers-between-locations",
    title: "Inventory transfers between GTA locations",
    description:
      "Practical guide to store-to-store and warehouse-to-store transfer capacity in the Greater Toronto Area — staging, vehicle class, and closeout proof.",
    intro:
      "Transfers look simple until freight is not staged, the dock contact is wrong, or nobody can prove the stock arrived. Treat transfers like customer deliveries: capacity, windows, tracking, and proof.",
    sections: [
      {
        heading: "Stage like a customer cut-off",
        body: "Ready freight, clear SKU references, and a reachable dock contact before dispatch. Late staging is still the top failure mode on internal moves.",
      },
      {
        heading: "Match the truck to the cube",
        body: "Totes and cartons need different capacity than pallet transfers. Confirm class in the quote so the first assignment can succeed.",
      },
      {
        heading: "Close with evidence",
        body: "Photo and GPS timestamps help warehouse and retail agree the transfer completed — and give loss-prevention a record when something is missing.",
      },
    ],
    industrySlugs: ["ecommerce", "construction-materials", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "workflow", label: "How delivery works" },
    ],
  },
  {
    slug: "choosing-courier-vs-capacity-partner-gta",
    title: "Choosing a courier vs a capacity partner in the GTA",
    description:
      "Practical guide for GTA B2B shippers comparing ad-hoc couriers with a transportation capacity partner — vehicles, drivers, ops, tracking, and proof.",
    intro:
      "When a jobsite window fails or a café route slips, the question is rarely “which app?” It is whether you have reliable vehicle-and-driver capacity with dispatch, tracking, and proof — or another phone number that may not answer at peak. Use this guide to choose the right pattern for GTA B2B freight.",
    sections: [
      {
        heading: "What you are really buying",
        body: "A courier trip buys a one-off move. A capacity partner sells executed transportation: matched vehicle class, professional driver, dispatch when exceptions hit, and closeout evidence your finance team can use. Software may sit behind both — but the SKU you should evaluate is capacity on the road.",
      },
      {
        heading: "When ad-hoc courier is enough",
        body: "Low volume, flexible windows, and freight that fits a sedan can work with occasional courier bookings. Failures are tolerable if receivers are flexible and you do not need recurring proof standards.",
      },
      {
        heading: "When you need a capacity partner",
        body: "Recurring café or wholesale loops, jobsite windows, multi-stop waves, overflow when your fleet is full, and claims-ready POD all point to a partner who can reserve or match capacity — not just quote a single trip.",
      },
      {
        heading: "Questions to ask before you switch",
        body: "What vehicle classes are available same-day? Who owns exception recovery? Is tracking shareable with receivers? Is photo/GPS/signature available on every stop you care about? Are prices confirmed in writing before dispatch?",
      },
    ],
    industrySlugs: ["construction-materials", "electrical-distribution", "coffee-roasters"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "pricing", label: "How pricing works" },
    ],
  },
  {
    slug: "same-day-from-store-capacity-gta",
    title: "Same-day capacity from your GTA store locations",
    description:
      "How GTA retailers and multi-location operators fulfill local orders from the nearest store — with vehicle-and-driver capacity, cut-offs, tracking, and proof. Not a checkout SaaS app.",
    intro:
      "Ship-from-store is a capacity problem: the branch that has stock must stage freight, the right vehicle must hit the window, and receivers need status they trust. PorterChain supplies that capacity across your GTA locations — as same-day or scheduled runs — without asking you to staff a courier desk in every store.",
    sections: [
      {
        heading: "Pick up where the inventory actually is",
        body: "Wrong-branch staging kills same-day promises. Align pickup to the store or counter that can pull the order, with clear cut-offs by location. Multi-location routing keeps one capacity partner across branches.",
      },
      {
        heading: "Customer promise vs ops ticket",
        body: "Whether checkout shows same-day or standard shipping, ops still needs vehicle class, access notes, and proof. Treat every store-origin run like a commercial delivery — not an afterthought courier text.",
      },
      {
        heading: "Overflow when a location spikes",
        body: "Peak days empty one store and overload another. Use transfer capacity to rebalance, then outbound capacity for customer drops — same tracking and POD standards end to end.",
      },
      {
        heading: "What this is not",
        body: "This is transportation capacity for store-origin and branch-origin freight. It is not a Shopify install, item-substitution merchandising app, or inventory system. You keep commerce and stock systems; we execute the move.",
      },
    ],
    industrySlugs: ["ecommerce", "coffee-roasters", "construction-materials"],
    serviceAreaSlugs: ["toronto", "mississauga", "brampton", "vaughan"],
    extraLinks: [
      { path: "onboarding", label: quoteCtaLabel("en") },
      { path: "serviceAreas", label: "Service areas" },
    ],
  },
];

export function getAuthorityPageBySlug(slug: string): AuthorityPage | null {
  return AUTHORITY_PAGES.find((p) => p.slug === slug) ?? null;
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
