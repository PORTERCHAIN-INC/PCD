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

/** Full fleet lineup — sedan through box truck (MAIN brand image, 2560px source; served as AVIF/WebP). */
export const BRAND_FLEET_LINEUP = localImg(
  "/images/brand/fleet-lineup.jpg",
  "Porterchain green fleet — sedan, SUV, van, and box truck — moving commerce on chain",
  2560,
  1454
);

/** Brand fleet at the dock — box truck + trailer (legacy dock pair). */
export const BRAND_DOCK_PAIR = localImg(
  "/images/brand/moving-commerce-on-chain.jpg",
  "Porterchain box truck and trailer at a warehouse — moving commerce on chain",
  2048,
  1176
);

/** Overhead fleet lined at the depot — network capacity at scale. */
export const BRAND_FLEET_DEPOT = localImg(
  "/images/brand/fleet-depot.jpg",
  "Porterchain green delivery fleet parked at the depot — moving commerce on chain",
  2048,
  1162
);

/** Dock briefing — drivers with clipboard beside branded truck. */
export const BRAND_WAREHOUSE_DOCK = localImg(
  "/images/brand/warehouse-dock.jpg",
  "Porterchain drivers reviewing a delivery clipboard beside a branded truck at the warehouse dock",
  2048,
  1176
);

/** Urban same-day run — truck in motion through the city. */
export const BRAND_URBAN_DELIVERY = localImg(
  "/images/brand/urban-delivery.jpg",
  "Porterchain green box truck on an urban delivery route — moving commerce on chain",
  2048,
  1176
);

/** Warehouse loading — team loading freight into a branded truck. */
export const BRAND_WAREHOUSE_LOADING = localImg(
  "/images/brand/warehouse-loading.jpg",
  "Porterchain team loading boxes into a branded green truck inside the warehouse",
  2048,
  1176
);

/** Open road — branded box truck on the highway (business / services hero). */
export const BRAND_OPEN_ROAD = localImg(
  "/images/brand/open-road.jpg",
  "Porterchain green box truck on the open highway — moving commerce on chain",
  2560,
  1454
);

/** @deprecated Homepage uses GtaAiRouteVisual — kept for blog / legacy refs. */
export const ROUTE_OPTIMIZATION_HOME = localImg(
  "/images/stock/toronto-gta-skyline-landscape.jpg",
  "Greater Toronto Area skyline — Porterchain route planning across Toronto, Peel, and York",
  1024,
  734
);

/** Guaranteed-working fallback when a remote image fails to load. */
export const FALLBACK_IMAGE = img(
  "photo-1766959481554-5a7bb490758a",
  "Commercial delivery vehicle on route",
  1920,
  1280
);

export const siteImages = {
  brand: {
    /** MAIN brand image — full fleet lineup */
    main: BRAND_FLEET_LINEUP,
    lineup: BRAND_FLEET_LINEUP,
    /** Exclusive page owners — do not reuse across surfaces. */
    dockPair: BRAND_DOCK_PAIR,
    depot: BRAND_FLEET_DEPOT,
    warehouseDock: BRAND_WAREHOUSE_DOCK,
    urban: BRAND_URBAN_DELIVERY,
    loading: BRAND_WAREHOUSE_LOADING,
    /** Business / services hero — exclusive */
    openRoad: BRAND_OPEN_ROAD,
    /** @deprecated alias — prefer dockPair */
    fleet: BRAND_DOCK_PAIR,
    /** @deprecated alias — prefer main */
    tagline: BRAND_FLEET_LINEUP,
  },
  home: {
    smartRouting: ROUTE_OPTIMIZATION_HOME,
    routeOptimization: ROUTE_OPTIMIZATION_HOME,
  },
  hero: {
    /** Home only — MAIN fleet lineup */
    welcome: BRAND_FLEET_LINEUP,
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
    /** Vehicle partner uses brand.warehouseDock explicitly — keep stock here as unused alias */
    partner: img("photo-1449965408869-eaa3f722e40d", "Driver partner preparing a delivery vehicle"),
  },
  vehicles: {
    sedan: localImg(
      "/images/brand/vehicles/sedan.jpg",
      "PorterChain branded sedan at a GTA warehouse — moving commerce on chain",
      1024,
      585
    ),
    suv: localImg(
      "/images/brand/vehicles/suv.jpg",
      "PorterChain branded SUV for multi-stop delivery — moving commerce on chain",
      1024,
      585
    ),
    pickup: localImg(
      "/images/brand/vehicles/pickup.jpg",
      "PorterChain branded pickup truck for jobsite and local freight — moving commerce on chain",
      1024,
      585
    ),
    "cargo-van": localImg(
      "/images/brand/vehicles/cargo-van.jpg",
      "PorterChain branded cargo van at a GTA warehouse — moving commerce on chain",
      1024,
      581
    ),
    "high-roof": localImg(
      "/images/brand/vehicles/cargo-van.jpg",
      "PorterChain branded high-roof cargo van for B2B delivery — moving commerce on chain",
      1024,
      581
    ),
    "box-16": localImg(
      "/images/brand/vehicles/box-truck.jpg",
      "PorterChain branded box truck at warehouse docks — moving commerce on chain",
      1024,
      585
    ),
    "box-20": localImg(
      "/images/brand/vehicles/box-truck.jpg",
      "PorterChain branded box truck for palletized freight — moving commerce on chain",
      1024,
      585
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
  if (lower.includes("vehicle-partner") || lower.includes("drive"))
    return siteImages.brand.warehouseDock;
  if (lower.includes("sedan")) return siteImages.vehicles.sedan;
  if (lower.includes("suv")) return siteImages.vehicles.suv;
  if (lower.includes("pickup")) return siteImages.vehicles.pickup;
  if (lower.includes("cargo-van") || lower.includes("trade-van"))
    return siteImages.vehicles["cargo-van"];
  if (lower.includes("van")) return siteImages.vehicles["cargo-van"];
  if (lower.includes("box-truck") || lower.includes("truck") || lower.includes("medium"))
    return siteImages.vehicles["box-16"];
  if (lower.includes("construction")) return siteImages.industries.construction;
  if (lower.includes("electrical")) return siteImages.industries.electrical;
  if (lower.includes("plumbing")) return siteImages.industries.plumbing;
  if (lower.includes("ecommerce")) return siteImages.industries.ecommerce;
  if (lower.includes("service-area") || lower.includes("local-delivery"))
    return siteImages.hero.toronto;
  if (lower.includes("success")) return siteImages.industries.construction;
  // Brand photos are page-exclusive (home / company / business / partner / platform).
  // Do not map SEO hubs onto them — use GTA stock instead.
  return siteImages.hero.gta;
}
