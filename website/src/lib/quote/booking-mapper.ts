import { bookingVehicleToEngine } from "@/lib/pricing/vehicle-map";
import type { CargoLoadType, QuoteItemInput, QuoteRequest, ShipmentMode, Urgency } from "./types";

export type BookingQuoteInput = {
  pickup: { formatted: string; lat?: number; lng?: number };
  dropoff: { formatted: string; lat?: number; lng?: number };
  vehicleClass: string;
  packageType: string;
  weightKg?: number;
  dimensions?: string;
  scheduleMode: "now" | "later";
  scheduledAt: Date;
};

const PARCEL_PACKAGES = new Set([
  "looseParcel",
  "documents",
  "medical",
  "furniture",
  "foodBeverage",
  "construction",
]);

function parseDimensions(
  dimensions: string
): { length: number; width: number; height: number } | null {
  const parts = dimensions
    .split(/[x×]/i)
    .map((part) => parseFloat(part.replace(/[^\d.]/g, "")))
    .filter((n) => !Number.isNaN(n));

  if (parts.length >= 3) {
    return { length: parts[0], width: parts[1], height: parts[2] };
  }
  return null;
}

function defaultItem(weightKg?: number): QuoteItemInput {
  return {
    weight: weightKg && weightKg > 0 ? weightKg : 5,
    length: 12,
    width: 12,
    height: 12,
    quantity: 1,
  };
}

function buildItems(input: BookingQuoteInput): QuoteItemInput[] {
  const parsed = input.dimensions ? parseDimensions(input.dimensions) : null;
  const weight = input.weightKg && input.weightKg > 0 ? input.weightKg : 5;

  if (parsed) {
    return [
      {
        weight,
        length: parsed.length,
        width: parsed.width,
        height: parsed.height,
        quantity: 1,
      },
    ];
  }

  return [defaultItem(input.weightKg)];
}

function resolveCargoLoadType(packageType: string): CargoLoadType {
  if (packageType === "ltlPallet") return "ltl";
  if (packageType === "ftlLoad") return "ftl";
  if (PARCEL_PACKAGES.has(packageType)) return "parcel";
  return "parcel";
}

function resolveUrgency(scheduleMode: "now" | "later"): Urgency {
  return scheduleMode === "now" ? "same_day" : "scheduled";
}

export function buildQuoteRequestFromBooking(input: BookingQuoteInput): QuoteRequest {
  const cargoLoadType = resolveCargoLoadType(input.packageType);
  const urgency = resolveUrgency(input.scheduleMode);
  const isWholeVehicle = input.packageType === "ftlLoad";

  const shipmentMode: ShipmentMode = isWholeVehicle ? "whole_vehicle" : "cargo";
  const preferredVehicleId = isWholeVehicle
    ? bookingVehicleToEngine(input.vehicleClass)
    : undefined;

  return {
    pickup: {
      address: input.pickup.formatted,
      latitude: input.pickup.lat,
      longitude: input.pickup.lng,
    },
    dropoff: {
      address: input.dropoff.formatted,
      latitude: input.dropoff.lat,
      longitude: input.dropoff.lng,
    },
    items: isWholeVehicle ? [] : buildItems(input),
    urgency,
    scheduledTime: input.scheduledAt.toISOString(),
    needHelper: false,
    cargoLoadType,
    shipmentMode,
    preferredVehicleId,
  };
}
