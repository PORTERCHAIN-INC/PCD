import type { BookingVehicleKey } from "@/lib/vehicle-keys";
import type { VehicleClassId } from "@/lib/quote/types";

/** Maps booking widget vehicle keys to the pricing engine vehicle IDs. */
export const BOOKING_TO_ENGINE_VEHICLE: Record<BookingVehicleKey, VehicleClassId> = {
  sedan: "sedan",
  suv: "suv",
  pickup: "cargo_van",
  cargoVan: "cargo_van",
  highRoof: "sprinter_van",
  box16: "box_16ft",
  box20: "box_20ft",
};

export function bookingVehicleToEngine(key: string): VehicleClassId {
  return BOOKING_TO_ENGINE_VEHICLE[key as BookingVehicleKey] ?? "cargo_van";
}
