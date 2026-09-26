/** Capacity Catalog SoT1 — snake ids only (matches customer_goods / vehicle_types). */

export const CAPACITY_CLASS_IDS = [
  "sedan_suv",
  "pickup",
  "cargo_van",
  "sprinter_van",
  "box_16",
  "box_20",
] as const;

export type CapacityClassId = (typeof CAPACITY_CLASS_IDS)[number];

export const DEFAULT_CAPACITY_CLASS: CapacityClassId = "cargo_van";

/** Display English — keep in sync with Capacity Catalog `default_vehicle_catalog` labels. */
export const CAPACITY_CLASS_LABELS: Record<CapacityClassId, string> = {
  sedan_suv: "Sedan / SUV",
  pickup: "Pickup",
  cargo_van: "Cargo van",
  sprinter_van: "Sprinter / high-roof",
  box_16: "16 ft box",
  box_20: "20 ft box",
};

/** Legacy / marketing keys → same English (never invent a second dialect). */
const VEHICLE_LABEL_ALIASES: Record<string, string> = {
  sedan: "Sedan / SUV",
  suv: "Sedan / SUV",
  sedanSuv: "Sedan / SUV",
  cargoVan: "Cargo van",
  highRoof: "Sprinter / high-roof",
  box16: "16 ft box",
  box20: "20 ft box",
  boxTruck: "16 ft box",
  box_truck: "16 ft box",
};

export const CAPACITY_CLASS_OPTIONS = CAPACITY_CLASS_IDS.map((id) => ({
  id,
  label: CAPACITY_CLASS_LABELS[id],
}));

export function vehicleLabel(code?: string | null, fallback = "—"): string {
  if (code == null) return fallback;
  const raw = String(code).trim();
  if (!raw) return fallback;
  if (raw in CAPACITY_CLASS_LABELS) {
    return CAPACITY_CLASS_LABELS[raw as CapacityClassId];
  }
  if (raw in VEHICLE_LABEL_ALIASES) {
    return VEHICLE_LABEL_ALIASES[raw];
  }
  return raw.replace(/_/g, " ");
}
