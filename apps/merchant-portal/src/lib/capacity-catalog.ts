/**
 * Offline fallback for Capacity Catalog SoT1 (customer_goods.default_vehicle_catalog).
 * Prefer live booking-catalog when available; do not invent a second capacity table.
 */

export type CapacityCatalogRow = {
  id: string;
  label: string;
  capacityKg: number;
  bayCm: [number, number, number];
  passenger: boolean;
  band: "sedan" | "cargo_van" | "box_truck";
  bandLabel: string;
};

/** Mirror of apps/api .../customer_goods.default_vehicle_catalog() dims. */
export const CAPACITY_CATALOG_FALLBACK: CapacityCatalogRow[] = [
  {
    id: "sedan_suv",
    label: "Sedan / SUV",
    capacityKg: 80,
    bayCm: [120, 90, 80],
    passenger: true,
    band: "sedan",
    bandLabel: "Sedan",
  },
  {
    id: "pickup",
    label: "Pickup",
    capacityKg: 500,
    bayCm: [180, 150, 60],
    passenger: false,
    band: "sedan",
    bandLabel: "Sedan",
  },
  {
    id: "cargo_van",
    label: "Cargo van",
    capacityKg: 900,
    bayCm: [300, 170, 160],
    passenger: false,
    band: "cargo_van",
    bandLabel: "Cargo van",
  },
  {
    id: "sprinter_van",
    label: "Sprinter / high-roof",
    capacityKg: 1200,
    bayCm: [330, 170, 180],
    passenger: false,
    band: "cargo_van",
    bandLabel: "Cargo van",
  },
  {
    id: "box_16",
    label: "16 ft box truck",
    capacityKg: 3000,
    bayCm: [480, 240, 240],
    passenger: false,
    band: "box_truck",
    bandLabel: "Box truck",
  },
  {
    id: "box_20",
    label: "20 ft box truck",
    capacityKg: 4500,
    bayCm: [600, 240, 240],
    passenger: false,
    band: "box_truck",
    bandLabel: "Box truck",
  },
];

const LEGACY_TO_CATALOG: Record<string, string> = {
  sedan: "sedan_suv",
  suv: "sedan_suv",
  sedan_suv: "sedan_suv",
  cargoVan: "cargo_van",
  cargo_van: "cargo_van",
  highRoof: "sprinter_van",
  sprinter_van: "sprinter_van",
  box16: "box_16",
  box_16: "box_16",
  box20: "box_20",
  box_20: "box_20",
};

export function canonicalizeCapacityClassId(raw: string | null | undefined): string {
  const key = (raw || "").trim();
  if (!key) return "cargo_van";
  return LEGACY_TO_CATALOG[key] || LEGACY_TO_CATALOG[key.replace(/-/g, "_")] || key;
}
