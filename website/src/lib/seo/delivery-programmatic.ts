/**
 * Programmatic "/delivery/{industry}/{area}" pages — data + pure builders.
 *
 * Zero imports on purpose: Node's built-in test runner imports this file
 * directly (type stripping), and the pages, sitemap and JSON-LD all read the
 * same source of truth.
 *
 * Areas are groups of GTA forward sortation areas (FSAs) taken from the pricing
 * registry (services/pricing-engine/porterchain_pricing/data/gta150_fsa_registry.json).
 * Centroids and distances are the mean of the member FSAs in that registry.
 */

export type VehicleId = "sedan_suv" | "cargo_van" | "box_16";

export type DeliveryVehicle = {
  id: VehicleId;
  label: string;
  /** Drivers need only a standard Ontario G licence for every class we sell. */
  licence: "G";
  capacity: string;
  bestFor: string;
};

export const DELIVERY_VEHICLES: Record<VehicleId, DeliveryVehicle> = {
  sedan_suv: {
    id: "sedan_suv",
    label: "Sedan / SUV",
    licence: "G",
    capacity: "up to about 80 kg — totes, bags, small cartons",
    bestFor: "prescriptions, specimens, documents and small e-commerce parcels",
  },
  cargo_van: {
    id: "cargo_van",
    label: "Cargo van",
    licence: "G",
    capacity: "up to about 900 kg — cartons, fittings, small pallets",
    bestFor: "multi-drop parcel runs, trade counter orders and wholesale cartons",
  },
  box_16: {
    id: "box_16",
    label: "16 ft box truck",
    licence: "G",
    capacity: "up to about 3,000 kg — pallets and bulky freight",
    bestFor: "pallets, warehouse transfers and building materials",
  },
};

/** Default same-day wave — mirrors the pricing-engine `delivery_promise` default
 * (an example value until ops confirm; the quote always shows the real window). */
export const DELIVERY_PROMISE_DEFAULT = {
  cutoff: "11:00",
  windowStart: "14:00",
  windowEnd: "21:00",
  days: "Monday to Saturday",
} as const;

export type DistanceBand = "core" | "inner" | "outer";

export type DeliveryArea = {
  slug: string;
  name: string;
  /** Municipality / region used in schema and copy. */
  locality: string;
  fsas: string[];
  lat: number;
  lng: number;
  /** Mean distance of the member FSAs from the downtown Toronto hub, km. */
  distanceKm: number;
  /** Has meaningful industrial / warehouse land (warehouse + wholesale pages). */
  industrial: boolean;
  /** Existing /service-areas/{slug} page to link to, when there is one. */
  serviceAreaSlug?: string;
  corridors: string;
  businessMix: string;
};

export const DELIVERY_AREAS: DeliveryArea[] = [
  {
    slug: "downtown-toronto",
    name: "Downtown Toronto",
    locality: "Toronto",
    fsas: "M5A M5B M5C M5E M5G M5H M5J M5M M5N M5P M5R M5S M5T M5V".split(" "),
    lat: 43.6666,
    lng: -79.3918,
    distanceKm: 2.6,
    industrial: false,
    serviceAreaSlug: "toronto",
    corridors: "the Financial District, King West, the Discovery District hospitals and Yorkville",
    businessMix: "clinics, pharmacies, condo job sites, boutiques and head offices",
  },
  {
    slug: "east-york-midtown",
    name: "Midtown & East Toronto",
    locality: "Toronto",
    fsas: "M4A M4B M4C M4E M4G M4H M4J M4K M4L M4M M4N M4P M4R M4S M4T M4V M4W M4X M4Y".split(" "),
    lat: 43.6936,
    lng: -79.3569,
    distanceKm: 5.7,
    industrial: false,
    serviceAreaSlug: "toronto",
    corridors: "Yonge–Eglinton, Leaside, the Danforth and Leslieville",
    businessMix: "independent retail, clinics, renovation trades and Shopify brands",
  },
  {
    slug: "west-toronto",
    name: "West Toronto",
    locality: "Toronto",
    fsas: "M6A M6B M6C M6E M6G M6H M6J M6K M6L M6M M6N M6P M6R M6S".split(" "),
    lat: 43.677,
    lng: -79.4511,
    distanceKm: 6.6,
    industrial: true,
    serviceAreaSlug: "toronto",
    corridors: "the Junction, Liberty Village, Dufferin and the Weston Road industrial pockets",
    businessMix: "makers, small warehouses, trade suppliers and online stores",
  },
  {
    slug: "north-york",
    name: "North York",
    locality: "Toronto",
    fsas: "M2H M2J M2K M2L M2M M2N M2P M2R M3A M3B M3C M3H M3J M3K M3L M3M M3N".split(" "),
    lat: 43.7599,
    lng: -79.4205,
    distanceKm: 13.1,
    industrial: true,
    serviceAreaSlug: "toronto",
    corridors: "the Highway 401 / 404 interchange, Downsview and the Duncan Mill business parks",
    businessMix: "distributors, labs, medical offices and wholesale importers",
  },
  {
    slug: "scarborough",
    name: "Scarborough",
    locality: "Toronto",
    fsas: "M1B M1C M1E M1G M1H M1J M1K M1L M1M M1N M1P M1R M1S M1T M1V M1W M1X".split(" "),
    lat: 43.7682,
    lng: -79.2485,
    distanceKm: 17.1,
    industrial: true,
    serviceAreaSlug: "toronto",
    corridors: "the Highway 401 corridor, Golden Mile and the Progress Avenue industrial area",
    businessMix: "food and goods wholesalers, warehouses, pharmacies and contractors",
  },
  {
    slug: "etobicoke",
    name: "Etobicoke",
    locality: "Toronto",
    fsas: "M8V M8W M8X M8Y M8Z M9A M9B M9C M9L M9M M9N M9P M9R M9V M9W".split(" "),
    lat: 43.6742,
    lng: -79.5407,
    distanceKm: 13.8,
    industrial: true,
    serviceAreaSlug: "toronto",
    corridors: "the Highway 427 / Gardiner junction and the Rexdale and Queensway industrial belts",
    businessMix: "3PL warehouses, building-supply yards, auto parts and distributors",
  },
  {
    slug: "mississauga",
    name: "Mississauga",
    locality: "Mississauga",
    fsas: "L4T L4V L4W L4X L4Y L4Z L5A L5B L5C L5E L5G L5H L5J L5K L5L L5M L5N L5R L5S L5T L5V L5W".split(
      " "
    ),
    lat: 43.6005,
    lng: -79.6454,
    distanceKm: 22.6,
    industrial: true,
    serviceAreaSlug: "mississauga",
    corridors: "the Pearson airport cargo zone, Highways 401 / 403 / 410 and Meadowvale",
    businessMix: "Canada's densest cluster of 3PLs, importers, pharma and e-commerce fulfilment",
  },
  {
    slug: "brampton",
    name: "Brampton",
    locality: "Brampton",
    fsas: "L6P L6R L6S L6T L6V L6W L6X L6Y L6Z L7A".split(" "),
    lat: 43.7089,
    lng: -79.7565,
    distanceKm: 31.0,
    industrial: true,
    serviceAreaSlug: "brampton",
    corridors: "the Highway 410 / 407 corridor and the Steeles Avenue industrial district",
    businessMix: "distribution centres, wholesale traders, trucking yards and trades",
  },
  {
    slug: "vaughan",
    name: "Vaughan",
    locality: "Vaughan",
    fsas: "L4H L4J L4K L4L L6A".split(" "),
    lat: 43.818,
    lng: -79.5364,
    distanceKm: 22.4,
    industrial: true,
    serviceAreaSlug: "vaughan",
    corridors: "Highways 400 / 407, Concord and the Vaughan Metropolitan Centre",
    businessMix: "building-supply, plumbing and electrical distributors and warehouses",
  },
  {
    slug: "markham",
    name: "Markham",
    locality: "Markham",
    fsas: "L3P L3R L3S L3T L6B L6C L6E L6G".split(" "),
    lat: 43.8689,
    lng: -79.2957,
    distanceKm: 25.2,
    industrial: true,
    serviceAreaSlug: "markham",
    corridors: "the Highway 404 / 407 tech corridor and Steeles Avenue business parks",
    businessMix: "tech hardware, labs, importers and online retailers",
  },
  {
    slug: "richmond-hill",
    name: "Richmond Hill",
    locality: "Richmond Hill",
    fsas: "L4B L4C L4E L4S".split(" "),
    lat: 43.8951,
    lng: -79.4272,
    distanceKm: 27.1,
    industrial: true,
    corridors: "the Highway 404 / 407 business parks along Leslie Street and Beaver Creek",
    businessMix: "medical offices, labs, importers and trade counters",
  },
  {
    slug: "oakville",
    name: "Oakville",
    locality: "Oakville",
    fsas: "L6H L6J L6K L6L L6M".split(" "),
    lat: 43.4413,
    lng: -79.7096,
    distanceKm: 35.4,
    industrial: true,
    serviceAreaSlug: "oakville",
    corridors: "the QEW and Highway 403 / 407 employment lands",
    businessMix: "pharmacies, clinics, renovation trades and light manufacturing",
  },
  {
    slug: "burlington",
    name: "Burlington",
    locality: "Burlington",
    fsas: "L7L L7M L7N L7P L7R L7S L7T".split(" "),
    lat: 43.3548,
    lng: -79.8206,
    distanceKm: 48.6,
    industrial: true,
    serviceAreaSlug: "burlington",
    corridors: "the QEW / Highway 407 junction and the North Service Road industrial strip",
    businessMix: "distributors, building-supply yards and medical offices",
  },
  {
    slug: "hamilton",
    name: "Hamilton",
    locality: "Hamilton",
    fsas: "L8B L8E L8G L8H L8J L8K L8L L8M L8N L8P L8R L8S L8T L8V L8W L9A L9B L9C L9G L9H L9K".split(
      " "
    ),
    lat: 43.2415,
    lng: -79.8659,
    distanceKm: 60.5,
    industrial: true,
    serviceAreaSlug: "hamilton",
    corridors:
      "the Red Hill Valley Parkway, the bayfront industrial lands and the Lincoln Alexander",
    businessMix: "steel and fabrication, hospitals, wholesalers and contractors",
  },
  {
    slug: "pickering-ajax",
    name: "Pickering & Ajax",
    locality: "Pickering",
    fsas: "L1S L1T L1V L1W L1X L1Y L1Z".split(" "),
    lat: 43.853,
    lng: -79.0744,
    distanceKm: 33.7,
    industrial: true,
    serviceAreaSlug: "pickering",
    corridors: "the Highway 401 / 407 East corridor and the Ajax and Pickering business parks",
    businessMix: "warehouses, trade counters, pharmacies and home-based Shopify brands",
  },
  {
    slug: "oshawa-whitby",
    name: "Oshawa & Whitby",
    locality: "Oshawa",
    fsas: "L1G L1H L1J L1K L1L L1M L1N L1P L1R".split(" "),
    lat: 43.9165,
    lng: -78.9004,
    distanceKm: 48.7,
    industrial: true,
    serviceAreaSlug: "oshawa",
    corridors: "Highway 401 / 412 / 407 East and the Champlain Avenue and Thickson Road districts",
    businessMix: "auto-sector suppliers, contractors, distributors and clinics",
  },
  {
    slug: "milton",
    name: "Milton",
    locality: "Milton",
    fsas: "L9E L9T".split(" "),
    lat: 43.5177,
    lng: -79.8674,
    distanceKm: 41.9,
    industrial: true,
    corridors: "the Highway 401 / James Snow Parkway logistics parks",
    businessMix: "large distribution centres and building-supply yards",
  },
  {
    slug: "newmarket-aurora",
    name: "Newmarket & Aurora",
    locality: "Newmarket",
    fsas: "L3X L3Y L4G".split(" "),
    lat: 44.0335,
    lng: -79.4862,
    distanceKm: 43.1,
    industrial: true,
    corridors: "the Highway 404 extension and the Mulock / Wellington business parks",
    businessMix: "clinics, pharmacies, contractors and regional distributors",
  },
];

export type DeliveryFaq = { question: string; answer: string };

export type DeliveryVertical = {
  slug: string;
  name: string;
  /** Lower-case noun used inside sentences. */
  noun: string;
  audience: string;
  goods: string;
  vehicles: VehicleId[];
  /** Late arrival breaks the job (meds, specimens) — far areas are noindexed. */
  sameDayCritical: boolean;
  /** Only meaningful where there is industrial land. */
  industrialOnly: boolean;
  /** Existing /industry/{slug} page for internal linking. */
  industryPageSlug?: string;
  handling: string[];
  compliance: string;
  specialistFaq: DeliveryFaq;
  /** Per-vertical CTA variant. */
  cta: { label: string; pitch: string };
  /** Hero copy for the A/B flag; `control` is what ships when the flag is off. */
  hero: { control: string; variantB: string };
};

export const DELIVERY_VERTICALS: DeliveryVertical[] = [
  {
    slug: "shopify-merchants",
    name: "Shopify & e-commerce merchants",
    noun: "e-commerce order",
    audience: "Shopify and online stores shipping to GTA customers",
    goods: "customer orders, local same-day parcels and returns",
    vehicles: ["sedan_suv", "cargo_van"],
    sameDayCritical: false,
    industrialOnly: false,
    industryPageSlug: "ecommerce",
    handling: [
      "Orders flow in from the PorterChain Shopify app — no CSV uploads",
      "Customers get a live tracking link and photo proof of delivery",
      "Failed attempts follow your re-attempt / return policy",
    ],
    compliance:
      "Delivery and tracking messages are transactional; marketing messages to your customers stay under your own CASL consent.",
    specialistFaq: {
      question: "Can I offer same-day delivery at Shopify checkout?",
      answer:
        "Yes. The PorterChain Shopify app adds a same-day rate at checkout using the same pricing engine as this page's calculator, then books the run when the order is paid.",
    },
    cta: {
      label: "Price a Shopify delivery",
      pitch: "See a live same-day price for your next order.",
    },
    hero: {
      control: "Same-day Shopify order delivery",
      variantB: "Give your Shopify customers delivery today",
    },
  },
  {
    slug: "pharmacy",
    name: "Pharmacy delivery",
    noun: "prescription",
    audience: "independent and chain pharmacies, compounding labs and clinics",
    goods: "prescriptions, compounded medication and medical supplies",
    vehicles: ["sedan_suv"],
    sameDayCritical: true,
    industrialOnly: false,
    industryPageSlug: "pharmacy-medical",
    handling: [
      "Signature or ID check on delivery when you require it",
      "No safe-place drops for controlled items",
      "Sealed bags stay closed; drivers never handle patient information beyond the label",
    ],
    compliance:
      "Patient details are limited to what the driver needs to deliver (name, address, phone) and are handled under PIPEDA.",
    specialistFaq: {
      question: "Can drivers collect a signature or check ID for prescriptions?",
      answer:
        "Yes. Turn on signature and ID requirements in your delivery rules; the requirement is shown to the driver for every stop and the proof is stored with the order.",
    },
    cta: {
      label: "Price a prescription run",
      pitch: "Live price for a same-day pharmacy delivery.",
    },
    hero: {
      control: "Same-day pharmacy delivery",
      variantB: "Get prescriptions to patients today",
    },
  },
  {
    slug: "labs",
    name: "Lab & specimen courier",
    noun: "specimen",
    audience: "medical labs, clinics, research facilities and veterinary practices",
    goods: "specimens, samples, test kits and lab supplies",
    vehicles: ["sedan_suv"],
    sameDayCritical: true,
    industrialOnly: false,
    industryPageSlug: "lab-sample-delivery",
    handling: [
      "Scheduled daily pickups or on-demand STAT runs",
      "Chain-of-custody timestamps at pickup and drop-off",
      "Coolers and totes stay upright and sealed",
    ],
    compliance:
      "Specimens travel exactly as your staff packed and labelled them; anything classed as dangerous goods must be cleared with us before booking.",
    specialistFaq: {
      question: "Do you handle UN3373 Category B specimens?",
      answer:
        "Packages must be packed and labelled by your facility (for example UN3373 triple packaging). Drivers do not open, repack or relabel specimens; confirm any dangerous-goods requirement with us before booking.",
    },
    cta: { label: "Price a specimen run", pitch: "Live price for a lab pickup to drop-off." },
    hero: {
      control: "Same-day lab specimen courier",
      variantB: "Specimens to the lab before the cut-off",
    },
  },
  {
    slug: "warehouses",
    name: "Warehouse & 3PL overflow",
    noun: "warehouse transfer",
    audience: "3PLs, fulfilment centres and in-house warehouses",
    goods: "pallets, cartons, store replenishment and inter-site transfers",
    vehicles: ["cargo_van", "box_16"],
    sameDayCritical: false,
    industrialOnly: true,
    handling: [
      "Dock-to-dock transfers and multi-stop store replenishment",
      "Box trucks up to 16 ft for pallets; no special licence needed",
      "Overflow capacity on peak days without a long-term contract",
    ],
    compliance: "Photo and time-stamped proof of delivery is attached to every order.",
    specialistFaq: {
      question: "Can you take pallets?",
      answer:
        "Yes — a 16 ft box truck takes standard pallets. Tell us the count and weight when you book so the right vehicle is assigned.",
    },
    cta: { label: "Price a warehouse transfer", pitch: "Live price for a van or box-truck run." },
    hero: {
      control: "Same-day warehouse & 3PL overflow delivery",
      variantB: "Extra trucks for your busiest warehouse days",
    },
  },
  {
    slug: "wholesale-traders",
    name: "Wholesale & trading companies",
    noun: "wholesale order",
    audience: "importers, wholesalers and B2B traders",
    goods: "cartons, mixed SKUs and pallet-sized trade orders",
    vehicles: ["cargo_van", "box_16"],
    sameDayCritical: false,
    industrialOnly: true,
    handling: [
      "Multi-drop routes to retailers and restaurants",
      "Invoiced to your business account with proof of delivery",
      "Van or box truck matched to the order size",
    ],
    compliance: "Commercial invoices and proof of delivery are stored against each order.",
    specialistFaq: {
      question: "Can one van do several customer drops?",
      answer:
        "Yes. Book a multi-stop run and the driver follows the route order; each stop gets its own proof of delivery.",
    },
    cta: { label: "Price a wholesale drop", pitch: "Live price for a van or box-truck delivery." },
    hero: {
      control: "Same-day wholesale delivery",
      variantB: "Deliver trade orders the day they are placed",
    },
  },
  {
    slug: "construction",
    name: "Construction materials",
    noun: "job-site delivery",
    audience: "contractors, builders and building-supply yards",
    goods: "fixings, tools, drywall bundles, small pallets and site materials",
    vehicles: ["cargo_van", "box_16"],
    sameDayCritical: false,
    industrialOnly: false,
    industryPageSlug: "construction-materials",
    handling: [
      "Drops to the site contact with photo proof at the gate",
      "Early-morning and scheduled windows when the site needs them",
      "Box trucks for bundles; tail-gate delivery only (no cranes or flatbeds)",
    ],
    compliance:
      "Drivers follow site safety rules you share at booking (PPE, check-in, gate times).",
    specialistFaq: {
      question: "Do you deliver to active job sites?",
      answer:
        "Yes. Add the site contact and gate instructions when you book; the driver calls ahead and photographs the drop location.",
    },
    cta: {
      label: "Price a job-site delivery",
      pitch: "Live price for a van or box-truck site drop.",
    },
    hero: {
      control: "Same-day construction material delivery",
      variantB: "Keep crews working — materials on site today",
    },
  },
  {
    slug: "plumbing-electrical",
    name: "Plumbing & electrical parts",
    noun: "parts order",
    audience: "plumbing, HVAC and electrical supply houses and their trade customers",
    goods: "fittings, valves, wire, breakers, fixtures and small equipment",
    vehicles: ["sedan_suv", "cargo_van", "box_16"],
    sameDayCritical: false,
    industrialOnly: false,
    industryPageSlug: "plumbing-supply",
    handling: [
      "Counter-to-van runs for contractors waiting on a part",
      "Branch-to-branch stock transfers",
      "Photo proof of delivery to the site or service van",
    ],
    compliance: "Proof of delivery and order references are kept for your trade-account invoicing.",
    specialistFaq: {
      question: "Can you run a part from our counter to a contractor's van?",
      answer:
        "Yes. Book a single-stop run with the contractor's phone number; the driver meets them at the site or van.",
    },
    cta: { label: "Price a parts run", pitch: "Live price for a counter-to-site delivery." },
    hero: {
      control: "Same-day plumbing & electrical parts delivery",
      variantB: "Get the missing part to the job today",
    },
  },
];

// ---------------------------------------------------------------- selection

export function distanceBand(km: number): DistanceBand {
  if (km < 15) return "core";
  if (km < 40) return "inner";
  return "outer";
}

export function getDeliveryVertical(slug: string): DeliveryVertical | undefined {
  return DELIVERY_VERTICALS.find((v) => v.slug === slug);
}

export function getDeliveryArea(slug: string): DeliveryArea | undefined {
  return DELIVERY_AREAS.find((a) => a.slug === slug);
}

/** Only meaningful combinations are generated at all. */
export function isFitCombination(vertical: DeliveryVertical, area: DeliveryArea): boolean {
  if (vertical.industrialOnly && !area.industrial) return false;
  return true;
}

/**
 * Weak pages are rendered (they help users) but `noindex`:
 * - areas with fewer than 3 FSAs (too little unique coverage detail), and
 * - time-critical verticals in outer areas (> 45 km) where the promise is weaker.
 */
export function indexability(
  vertical: DeliveryVertical,
  area: DeliveryArea
): { index: boolean; reason?: string } {
  if (!isFitCombination(vertical, area)) return { index: false, reason: "not_a_fit" };
  if (area.fsas.length < 3) return { index: false, reason: "thin_coverage" };
  if (vertical.sameDayCritical && area.distanceKm > 45) {
    return { index: false, reason: "time_critical_far" };
  }
  return { index: true };
}

export type DeliveryPageRef = {
  vertical: string;
  area: string;
  path: string;
  index: boolean;
  reason?: string;
};

export function deliveryPagePath(verticalSlug: string, areaSlug?: string): string {
  return areaSlug ? `delivery/${verticalSlug}/${areaSlug}` : `delivery/${verticalSlug}`;
}

export function listDeliveryPages(): DeliveryPageRef[] {
  const out: DeliveryPageRef[] = [];
  for (const vertical of DELIVERY_VERTICALS) {
    for (const area of DELIVERY_AREAS) {
      if (!isFitCombination(vertical, area)) continue;
      const idx = indexability(vertical, area);
      out.push({
        vertical: vertical.slug,
        area: area.slug,
        path: deliveryPagePath(vertical.slug, area.slug),
        index: idx.index,
        ...(idx.reason ? { reason: idx.reason } : {}),
      });
    }
  }
  return out;
}

export function areasForVertical(vertical: DeliveryVertical): DeliveryArea[] {
  return DELIVERY_AREAS.filter((a) => isFitCombination(vertical, a));
}

function haversineKm(a: { lat: number; lng: number }, b: { lat: number; lng: number }): number {
  const rad = Math.PI / 180;
  const dLat = (b.lat - a.lat) * rad;
  const dLng = (b.lng - a.lng) * rad;
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * Math.sin(dLng / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(h));
}

/** Nearest other areas (by centroid) that also fit the vertical. */
export function nearbyAreas(
  area: DeliveryArea,
  vertical?: DeliveryVertical,
  count = 4
): Array<DeliveryArea & { kmApart: number }> {
  return DELIVERY_AREAS.filter((a) => a.slug !== area.slug)
    .filter((a) => !vertical || isFitCombination(vertical, a))
    .map((a) => ({ ...a, kmApart: Math.round(haversineKm(area, a)) }))
    .sort((x, y) => x.kmApart - y.kmApart)
    .slice(0, count);
}

// ---------------------------------------------------------------- content

function joinList(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function vehicleLabels(vertical: DeliveryVertical): string {
  return joinList(vertical.vehicles.map((v) => DELIVERY_VEHICLES[v].label.toLowerCase()));
}

function bandSentence(area: DeliveryArea): string {
  const band = distanceBand(area.distanceKm);
  if (band === "core") {
    return `${area.name} sits about ${area.distanceKm} km from our downtown hub, so most same-day runs here are short city legs.`;
  }
  if (band === "inner") {
    return `${area.name} is in the inner GTA ring, about ${area.distanceKm} km from downtown, reached by highway in one leg.`;
  }
  return `${area.name} is in the outer GTA ring, about ${area.distanceKm} km from downtown — book before the cut-off and some outer postal codes may be offered next-day instead.`;
}

export type DeliveryPageContent = {
  metaTitle: string;
  metaDescription: string;
  h1: string;
  answer: string;
  quickFacts: Array<{ label: string; value: string }>;
  areaSummary: string;
  serviceDetails: string[];
  vehicles: DeliveryVehicle[];
  promise: string;
  faqs: DeliveryFaq[];
  nearby: Array<{ slug: string; name: string; kmApart: number }>;
};

export function promiseSentence(): string {
  const p = DELIVERY_PROMISE_DEFAULT;
  return `Order by ${p.cutoff} for delivery ${p.windowStart}–${p.windowEnd} the same day, ${p.days}. Later orders go out the next operating day. Your quote shows the exact window before you book.`;
}

export function buildDeliveryPageContent(
  vertical: DeliveryVertical,
  area: DeliveryArea
): DeliveryPageContent {
  const fsaCount = area.fsas.length;
  const fsaText = area.fsas.join(", ");
  const vehicles = vertical.vehicles.map((v) => DELIVERY_VEHICLES[v]);
  const near = nearbyAreas(area, vertical);
  const h1 = `${vertical.hero.control} in ${area.name}`;
  const answer = `PorterChain delivers ${vertical.goods} for ${vertical.audience} across ${area.name} — ${fsaCount} postal areas (${fsaText}). ${promiseSentence()} Vehicles: ${vehicleLabels(vertical)}, all driven on a standard G licence. Prices are calculated live from distance and vehicle — check yours in the calculator, no sign-up needed.`;
  const faqs: DeliveryFaq[] = [
    {
      question: `Do you offer same-day ${vertical.noun} delivery in ${area.name}?`,
      answer: `Yes. ${promiseSentence()}`,
    },
    {
      question: `Which ${area.name} postal codes do you cover?`,
      answer: `All ${fsaCount} forward sortation areas in ${area.name}: ${fsaText}. They are part of our GTA coverage (about 150 km around downtown Toronto).`,
    },
    {
      question: `Which vehicle should I book for ${vertical.noun}s?`,
      answer: vehicles.map((v) => `${v.label}: ${v.capacity}; best for ${v.bestFor}.`).join(" "),
    },
    {
      question: `How much does ${vertical.noun} delivery in ${area.name} cost?`,
      answer:
        "Price depends on the driving distance and the vehicle. The calculator on this site uses the same pricing engine as checkout and shows the total including HST before you share any contact details.",
    },
    {
      question: `How far is ${area.name} from downtown Toronto?`,
      answer: `About ${area.distanceKm} km on average from our downtown hub. ${bandSentence(area)}`,
    },
    vertical.specialistFaq,
  ];
  return {
    metaTitle: `${vertical.hero.control} in ${area.name} | PorterChain`,
    metaDescription: `Same-day ${vertical.noun} delivery across ${area.name} (${area.fsas.slice(0, 4).join(", ")}${fsaCount > 4 ? "…" : ""}). ${vehicleLabels(vertical)}; order by ${DELIVERY_PROMISE_DEFAULT.cutoff}. Get a live price.`,
    h1,
    answer,
    quickFacts: [
      { label: "Postal areas", value: `${fsaCount} FSAs` },
      { label: "From downtown", value: `≈ ${area.distanceKm} km` },
      {
        label: "Same-day cut-off",
        value: `${DELIVERY_PROMISE_DEFAULT.cutoff} → ${DELIVERY_PROMISE_DEFAULT.windowStart}–${DELIVERY_PROMISE_DEFAULT.windowEnd}`,
      },
      { label: "Vehicles", value: vehicles.map((v) => v.label).join(" · ") },
    ],
    areaSummary: `${area.name} covers ${area.corridors}, home to ${area.businessMix}. ${bandSentence(area)}`,
    serviceDetails: [...vertical.handling, vertical.compliance],
    vehicles,
    promise: promiseSentence(),
    faqs,
    nearby: near.map((a) => ({ slug: a.slug, name: a.name, kmApart: a.kmApart })),
  };
}

// ---------------------------------------------------------------- JSON-LD

type JsonObject = Record<string, unknown>;

function abs(baseUrl: string, path: string): string {
  return `${baseUrl.replace(/\/$/, "")}${path.startsWith("/") ? path : `/${path}`}`;
}

/** Honest Offer: currency + tax-inclusive flag and a link to the live calculator. No made-up price. */
export function buildQuoteOffer(baseUrl: string, locale: string): JsonObject {
  return {
    "@type": "Offer",
    priceCurrency: "CAD",
    availability: "https://schema.org/InStock",
    url: abs(baseUrl, `/${locale}/delivery-cost-calculator`),
    description:
      "Price is calculated per delivery from driving distance and vehicle type; the calculator shows the total including HST.",
    priceSpecification: {
      "@type": "PriceSpecification",
      priceCurrency: "CAD",
      valueAddedTaxIncluded: true,
    },
  };
}

export function buildDeliveryServiceJsonLd(
  vertical: DeliveryVertical,
  area: DeliveryArea,
  opts: { baseUrl: string; locale: string }
): JsonObject {
  const base = opts.baseUrl.replace(/\/$/, "");
  const url = abs(base, `/${opts.locale}/${deliveryPagePath(vertical.slug, area.slug)}`);
  return {
    "@context": "https://schema.org",
    "@type": "Service",
    "@id": `${url}#service`,
    name: `${vertical.hero.control} in ${area.name}`,
    serviceType: `${vertical.name} delivery`,
    description: `Same-day ${vertical.noun} delivery across ${area.name} by ${vehicleLabels(vertical)}.`,
    url,
    provider: { "@id": `${base}/#organization` },
    areaServed: {
      "@type": "Place",
      name: `${area.name}, Ontario`,
      geo: { "@type": "GeoCoordinates", latitude: area.lat, longitude: area.lng },
      address: {
        "@type": "PostalAddress",
        addressLocality: area.locality,
        addressRegion: "ON",
        addressCountry: "CA",
        postalCode: area.fsas,
      },
    },
    audience: { "@type": "BusinessAudience", name: vertical.audience },
    offers: buildQuoteOffer(base, opts.locale),
  };
}

export function buildDeliveryFaqJsonLd(faqs: DeliveryFaq[]): JsonObject | null {
  const items = faqs.filter((f) => f.question.trim() && f.answer.trim());
  if (!items.length) return null;
  return {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: items.map((f) => ({
      "@type": "Question",
      name: f.question,
      acceptedAnswer: { "@type": "Answer", text: f.answer },
    })),
  };
}

export function buildDeliveryBreadcrumbJsonLd(
  crumbs: Array<{ name: string; path: string }>,
  baseUrl: string
): JsonObject {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: crumbs.map((c, i) => ({
      "@type": "ListItem",
      position: i + 1,
      name: c.name,
      item: abs(baseUrl, c.path),
    })),
  };
}

export function deliveryBreadcrumbs(
  locale: string,
  vertical?: DeliveryVertical,
  area?: DeliveryArea
): Array<{ name: string; path: string }> {
  const crumbs = [
    { name: "Home", path: `/${locale}` },
    { name: "Same-day delivery", path: `/${locale}/delivery` },
  ];
  if (vertical) {
    crumbs.push({ name: vertical.name, path: `/${locale}/${deliveryPagePath(vertical.slug)}` });
  }
  if (vertical && area) {
    crumbs.push({
      name: area.name,
      path: `/${locale}/${deliveryPagePath(vertical.slug, area.slug)}`,
    });
  }
  return crumbs;
}

// ---------------------------------------------------------------- entity facts

/** Facts used by /facts, llms.txt and Organization copy — keep in sync with the API. */
export const ENTITY_FACTS = {
  name: "PorterChain",
  legalName: "Porterchain Logistics Inc.",
  what: "Same-day local delivery for businesses in the Greater Toronto Area, booked online or through the Shopify app.",
  hub: "Downtown Toronto (43.6532, -79.3832)",
  coverage:
    "About 150 km around downtown Toronto: Toronto, Peel, York, Durham, Halton and Hamilton — checked by postal code (FSA) at quote time.",
  coverageFsaCount: 357,
  hours:
    "Office Monday–Friday 08:00–18:00, Saturday 09:00–14:00 (Toronto time); deliveries Monday–Saturday.",
  vehicles: Object.values(DELIVERY_VEHICLES).map((v) => `${v.label} (${v.capacity})`),
  licence: "Every vehicle class is driven on a standard Ontario G licence.",
  pricing:
    "Per-delivery price from driving distance and vehicle type, with a base distance included; a downtown surcharge applies where relevant. Prices are shown including 13% HST before booking. Volume accounts can have a merchant rate card.",
  promise: promiseSentence(),
  verticals: DELIVERY_VERTICALS.map((v) => v.name),
  privacy:
    "Personal information is handled under PIPEDA; marketing email requires separate CASL consent and every message carries an unsubscribe link.",
} as const;
