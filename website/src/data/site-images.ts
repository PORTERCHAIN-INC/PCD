/**
 * Curated stock photography (Unsplash License — free for commercial use).
 * https://unsplash.com/license
 *
 * Photo IDs are verified against images.unsplash.com (404s replaced Jul 2026).
 */

export type SiteImageRef = {
  src: string;
  alt: string;
  width: number;
  height: number;
};

function unsplash(photoId: string, width = 1920, height = 1280): string {
  return `https://images.unsplash.com/${photoId}?auto=format&fit=crop&w=${width}&h=${height}&q=80`;
}

function img(photoId: string, alt: string, width = 1920, height = 1280): SiteImageRef {
  return { src: unsplash(photoId, width, height), alt, width, height };
}

function localImg(path: string, alt: string, width: number, height: number): SiteImageRef {
  return { src: path, alt, width, height };
}

/** Toronto / GTA skyline — landscape, hosted locally (Leonard Laub / Unsplash). */
export const TORONTO_GTA_SKYLINE = localImg(
  "/images/stock/toronto-gta-skyline-landscape.jpg",
  "Toronto skyline and CN Tower across Lake Ontario — Porterchain serves the Greater Toronto Area",
  1024,
  734
);

/** Porterchain branded truck loading e-commerce parcels — hosted locally. */
export const ECOMMERCE_TRUCK = localImg(
  "/images/stock/ecommerce-porterchain-truck.jpg",
  "Porterchain branded delivery truck loading e-commerce parcels in a warehouse",
  768,
  1024
);

/** @deprecated Homepage uses GtaAiRouteVisual — kept for blog / legacy refs. */
export const ROUTE_OPTIMIZATION_HOME = localImg(
  "/images/stock/toronto-gta-skyline-landscape.jpg",
  "Greater Toronto Area skyline — Porterchain route planning across Toronto, Peel, and York",
  1024,
  734
);

/** @deprecated Use ROUTE_OPTIMIZATION_HOME */
export const SMART_ROUTING_DISPATCH = ROUTE_OPTIMIZATION_HOME;

/** Guaranteed-working fallback when a remote image fails to load. */
export const FALLBACK_IMAGE = img(
  "photo-1766959481554-5a7bb490758a",
  "Commercial delivery vehicle on route",
  1920,
  1280
);

export const siteImages = {
  home: {
    smartRouting: ROUTE_OPTIMIZATION_HOME,
    routeOptimization: ROUTE_OPTIMIZATION_HOME,
  },
  hero: {
    /** Branded Porterchain truck — homepage welcome hero */
    welcome: ECOMMERCE_TRUCK,
    delivery: img("photo-1766959481554-5a7bb490758a", "Delivery van on an urban route"),
    logistics: img(
      "photo-1600880292203-757bb62b4baf",
      "Warehouse team coordinating outbound freight"
    ),
    fleet: img("photo-1578575437130-527eed3abbec", "Commercial delivery fleet on the road"),
    toronto: TORONTO_GTA_SKYLINE,
    gta: TORONTO_GTA_SKYLINE,
    business: img(
      "photo-1600880292203-757bb62b4baf",
      "Operations team reviewing logistics in a warehouse"
    ),
    partner: img("photo-1449965408869-eaa3f722e40d", "Driver partner preparing a delivery vehicle"),
  },
  vehicles: {
    sedan: img("photo-1590362891991-f776e747a588", "Sedan used for local courier runs", 1200, 800),
    suv: img(
      "photo-1606664515524-ed2f786a0bd6",
      "SUV with cargo space for multi-stop delivery",
      1200,
      800
    ),
    pickup: img(
      "photo-1559416523-140ddc3d238c",
      "Pickup truck for flexible local freight",
      1200,
      800
    ),
    "cargo-van": img(
      "photo-1558618666-fcd25c85cd64",
      "White cargo van for B2B delivery routes",
      1200,
      800
    ),
    "high-roof": img(
      "photo-1578575437130-527eed3abbec",
      "High-roof van on a delivery route",
      1200,
      800
    ),
    "box-16": img(
      "photo-1581092160562-40aa08e78837",
      "Box truck for palletized local freight",
      1200,
      800
    ),
    "box-20": img(
      "photo-1578575437130-527eed3abbec",
      "Medium box truck at a loading bay",
      1200,
      800
    ),
  },
  industries: {
    construction: img(
      "photo-1541888946425-d81bb19240f5",
      "Construction materials staged at a job site"
    ),
    electrical: img(
      "photo-1621905252507-b35492cc74b4",
      "Electrical supplies prepared for distribution"
    ),
    plumbing: img(
      "photo-1600585154340-be6161a56a0c",
      "Plumbing fixtures and pipe inventory in a supply house"
    ),
    coffee: img(
      "photo-1447933601403-0c6688de566e",
      "Coffee roastery packaging for outbound delivery"
    ),
    medical: img("photo-1576091160399-112ba8d25d1d", "Medical supplies handled with care"),
    pharmacy: img(
      "photo-1576091160550-2173dba999ef",
      "Pharmacy inventory ready for local dispatch"
    ),
    restaurant: img(
      "photo-1414235077428-338989a2e8c0",
      "Restaurant kitchen preparing catering orders"
    ),
    "food-distribution": img(
      "photo-1504674900247-0877df9cc836",
      "Fresh food prepared for distribution routes"
    ),
    wholesale: img(
      "photo-1600880292203-757bb62b4baf",
      "Wholesale distribution aisle with palletized stock"
    ),
    hvac: img("photo-1503387762-592deb58ef4e", "HVAC equipment staged for jobsite delivery"),
    "auto-parts": img(
      "photo-1486262715619-67b85e0b08d3",
      "Automotive parts organized for same-day delivery"
    ),
    retail: img("photo-1441986300917-64674bd600d8", "Retail stockroom preparing outbound parcels"),
    ecommerce: ECOMMERCE_TRUCK,
    manufacturing: img(
      "photo-1581091226825-a6a2a5aee158",
      "Manufacturing floor with outbound logistics"
    ),
    laboratories: img(
      "photo-1576086213369-97a306d36557",
      "Laboratory samples prepared for courier pickup"
    ),
    "print-shops": img(
      "photo-1586281380349-632531db7ed4",
      "Print shop finishing orders for local delivery"
    ),
  },
  blog: {
    logistics: img("photo-1600880292203-757bb62b4baf", "Commercial logistics operations"),
    technology: img(
      "photo-1460925895917-afdab827c52f",
      "Logistics analytics on a business dashboard"
    ),
    business: img("photo-1552664730-d307ca884978", "Business team planning delivery operations"),
    "route-optimization": img(
      "photo-1524661135-423995f22d0b",
      "Digital map with delivery stops and optimized route planning"
    ),
    "supply-chain": img(
      "photo-1600880292203-757bb62b4baf",
      "Supply chain inventory in a distribution center"
    ),
    "same-day-delivery": img(
      "photo-1766959481554-5a7bb490758a",
      "Same-day parcel handoff on a delivery route"
    ),
    wholesale: img("photo-1600880292203-757bb62b4baf", "Wholesale distribution operations"),
    construction: img("photo-1541888946425-d81bb19240f5", "Construction material logistics"),
    medical: img("photo-1576091160399-112ba8d25d1d", "Medical supply chain coordination"),
    retail: img("photo-1441986300917-64674bd600d8", "Retail last-mile fulfillment"),
    coffee: img("photo-1447933601403-0c6688de566e", "Coffee supply chain freshness"),
  },
  sections: {
    individuals: img(
      "photo-1556742049-0cfed4f6a45d",
      "Individual sending a local parcel",
      1200,
      900
    ),
    business: img(
      "photo-1556761175-5973dc0f32e7",
      "Business team coordinating recurring deliveries",
      1200,
      900
    ),
    howItWorks: img(
      "photo-1512941937669-90a1b58e7e9c",
      "Driver completing a delivery with mobile workflow",
      1200,
      900
    ),
    mobileApp: img(
      "photo-1512941937669-90a1b58e7e9c",
      "Mobile delivery workflow in the field",
      1200,
      900
    ),
    trust: TORONTO_GTA_SKYLINE,
    gta: TORONTO_GTA_SKYLINE,
  },
} as const;

const NICHE_HERO: Record<string, keyof typeof siteImages.industries> = {
  "construction-materials": "construction",
  "electrical-distribution": "electrical",
  "plumbing-supply": "plumbing",
  "coffee-roasters": "coffee",
  "pharmacy-medical": "pharmacy",
  cosmetics: "retail",
  chocolate: "food-distribution",
  "lab-sample-delivery": "laboratories",
  ecommerce: "ecommerce",
};

const VEHICLE_PARTNER_KEYS = {
  sedan: "sedan",
  suv: "suv",
  pickup: "pickup",
  van: "cargo-van",
  boxTruck: "box-16",
} as const;

export function getVehicleImage(type: string): SiteImageRef {
  const key = type as keyof typeof siteImages.vehicles;
  return siteImages.vehicles[key] ?? siteImages.vehicles.sedan;
}

export function getIndustryImage(industryId: string): SiteImageRef {
  const key = industryId as keyof typeof siteImages.industries;
  return siteImages.industries[key] ?? siteImages.industries.wholesale;
}

export function getNicheHeroImage(slug: string): SiteImageRef {
  const industryKey = NICHE_HERO[slug];
  return industryKey ? siteImages.industries[industryKey] : siteImages.hero.gta;
}

export function getVehiclePartnerImage(key: keyof typeof VEHICLE_PARTNER_KEYS): SiteImageRef {
  const vehicleKey = VEHICLE_PARTNER_KEYS[key];
  return getVehicleImage(vehicleKey);
}

export function getBlogCoverImage(category: string): SiteImageRef {
  const key = category as keyof typeof siteImages.blog;
  return siteImages.blog[key] ?? siteImages.blog.logistics;
}

export function getPageHeroImage(source: string): SiteImageRef {
  const lower = source.toLowerCase();
  if (lower.includes("vehicle-partner") || lower.includes("drive")) return siteImages.hero.partner;
  if (lower.includes("sedan")) return siteImages.vehicles.sedan;
  if (lower.includes("suv")) return siteImages.vehicles.suv;
  if (lower.includes("pickup")) return siteImages.vehicles.pickup;
  if (lower.includes("cargo-van")) return siteImages.vehicles["cargo-van"];
  if (lower.includes("van")) return siteImages.vehicles["cargo-van"];
  if (lower.includes("truck") || lower.includes("medium")) return siteImages.vehicles["box-16"];
  if (lower.includes("construction")) return siteImages.industries.construction;
  if (lower.includes("electrical")) return siteImages.industries.electrical;
  if (lower.includes("plumbing")) return siteImages.industries.plumbing;
  if (lower.includes("ecommerce")) return siteImages.industries.ecommerce;
  if (lower.includes("business")) return siteImages.hero.business;
  if (lower.includes("service-area") || lower.includes("local-delivery"))
    return siteImages.hero.toronto;
  if (lower.includes("campaign")) return siteImages.hero.delivery;
  if (lower.includes("success")) return siteImages.industries.construction;
  return siteImages.hero.gta;
}
