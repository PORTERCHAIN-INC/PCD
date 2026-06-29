export type Urgency = "scheduled" | "same_day" | "rush";

export type QuoteAddress = {
  address: string;
  latitude?: number;
  longitude?: number;
};

export type QuoteItemInput = {
  weight: number;
  length: number;
  width: number;
  height: number;
  quantity: number;
};

export type ShipmentMode = "cargo" | "whole_vehicle";

export type CargoLoadType = "parcel" | "skid" | "ltl" | "ftl";

export type QuoteRequest = {
  pickup: QuoteAddress;
  dropoff: QuoteAddress;
  additionalStops?: QuoteAddress[];
  items: QuoteItemInput[];
  urgency: Urgency;
  scheduledTime?: string;
  needHelper: boolean;
  photoCount?: number;
  /** Parcel, skid, LTL, or FTL — drives cargo form and sizing. */
  cargoLoadType?: CargoLoadType;
  /** Cargo-based sizing (default) or book an entire vehicle class. */
  shipmentMode?: ShipmentMode;
  preferredVehicleId?: VehicleClassId;
};

export type Coordinates = {
  latitude: number;
  longitude: number;
};

export type GeocodedAddress = QuoteAddress & Coordinates;

export type VehicleClassId =
  "sedan" | "suv" | "minivan" | "cargo_van" | "sprinter_van" | "box_16ft" | "box_20ft";

export type VehicleClass = {
  id: VehicleClassId;
  name: string;
  maxWeightKg: number;
  maxLengthCm: number;
  maxWidthCm: number;
  maxHeightCm: number;
  maxVolumeM3: number;
  baseFeeCad: number;
  perKmCad: number;
  perStopCad: number;
};

export type RouteResult = {
  distanceMeters: number;
  durationSeconds: number;
  distanceKm: number;
  durationMinutes: number;
};

export type ItemTotals = {
  totalWeightKg: number;
  totalVolumeM3: number;
  maxLengthCm: number;
  maxWidthCm: number;
  maxHeightCm: number;
  totalQuantity: number;
};

import type { TrafficResultCamel } from "@/lib/traffic";

export type QuoteBreakdown = {
  baseFee: number;
  distanceFee: number;
  timeFee: number;
  weightFee: number;
  fuelFee: number;
  stopFee: number;
  helperFee: number;
  subtotal: number;
  adjustedCost: number;
  trafficMultiplier: number;
  marginMultiplier: number;
  /** @deprecated Use trafficMultiplier */
  urgencyMultiplier: number;
};

export type QuoteResult = {
  quoteId: string;
  expiresAt: string;
  currency: "CAD";
  pickup: GeocodedAddress;
  dropoff: GeocodedAddress;
  additionalStops: GeocodedAddress[];
  route: RouteResult;
  items: ItemTotals;
  recommendedVehicle: VehicleClass;
  alternativeVehicles: VehicleClass[];
  weightUtilization: number;
  volumeUtilization: number;
  /** Customer-facing total price */
  price: number;
  customerPrice: number;
  driverPayout: number;
  platformMargin: number;
  breakdown: QuoteBreakdown;
  traffic: TrafficResultCamel;
  urgency: Urgency;
  scheduledTime?: string;
  needHelper: boolean;
  computedInMs: number;
  inServiceArea: boolean;
  warnings: string[];
};

export type QuoteError = {
  error: string;
  code:
    | "INVALID_INPUT"
    | "GEOCODE_FAILED"
    | "OUT_OF_SERVICE_AREA"
    | "NO_VEHICLE_FIT"
    | "ROUTING_FAILED"
    | "TIMEOUT";
};
