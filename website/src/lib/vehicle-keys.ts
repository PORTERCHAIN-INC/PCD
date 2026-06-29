export const BOOKING_VEHICLE_KEYS = [
  "sedan",
  "suv",
  "pickup",
  "cargoVan",
  "highRoof",
  "box16",
  "box20",
] as const;

export type BookingVehicleKey = (typeof BOOKING_VEHICLE_KEYS)[number];

export const CATALOG_TO_BOOKING: Record<string, BookingVehicleKey> = {
  sedan: "sedan",
  suv: "suv",
  pickup: "pickup",
  "cargo-van": "cargoVan",
  "high-roof": "highRoof",
  "box-16": "box16",
  "box-20": "box20",
};

export const BOOKING_TO_CATALOG: Record<BookingVehicleKey, string> = {
  sedan: "sedan",
  suv: "suv",
  pickup: "pickup",
  cargoVan: "cargo-van",
  highRoof: "high-roof",
  box16: "box-16",
  box20: "box-20",
};

export function catalogIdToBookingKey(catalogId: string): BookingVehicleKey {
  return CATALOG_TO_BOOKING[catalogId] ?? "cargoVan";
}

export function bookingKeyToCatalogId(key: string): string | null {
  return BOOKING_TO_CATALOG[key as BookingVehicleKey] ?? null;
}
