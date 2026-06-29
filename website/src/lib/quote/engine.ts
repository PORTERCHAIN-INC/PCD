import { recommendVehicle } from "./capacity";
import { calculateItemTotals } from "./dimensions";
import { geocodeAddresses } from "./geocode";
import { generateQuoteId, isInServiceArea, quoteExpiresAt } from "./quote-utils";
import { calculateQuotePrice } from "./pricing-bridge";
import { extractFsa } from "@/lib/traffic";
import { calculateRoute } from "./routing";
import { getVehicleById } from "./vehicles";
import type { ItemTotals, QuoteRequest, QuoteResult, QuoteError, VehicleClass } from "./types";

const QUOTE_DEADLINE_MS = 2800;

export async function computeQuote(request: QuoteRequest): Promise<QuoteResult | QuoteError> {
  const started = Date.now();

  try {
    const result = await Promise.race([
      runQuote(request, started),
      timeoutReject(QUOTE_DEADLINE_MS),
    ]);
    return result;
  } catch (err) {
    if (err instanceof Error && err.message === "QUOTE_TIMEOUT") {
      return { error: "Quote timed out. Please try again.", code: "TIMEOUT" };
    }
    const message = err instanceof Error ? err.message : "Quote calculation failed";
    if (message.includes("geocode")) {
      return { error: message, code: "GEOCODE_FAILED" };
    }
    if (message.includes("vehicle")) {
      return { error: message, code: "NO_VEHICLE_FIT" };
    }
    return { error: message, code: "ROUTING_FAILED" };
  }
}

async function runQuote(request: QuoteRequest, started: number): Promise<QuoteResult | QuoteError> {
  validateRequest(request);

  const stops = request.additionalStops ?? [];
  const allAddresses = [request.pickup, ...stops, request.dropoff];
  const geocoded = await geocodeAddresses(allAddresses);

  const pickup = geocoded[0];
  const dropoff = geocoded[geocoded.length - 1];
  const additionalStops = geocoded.slice(1, -1);

  const allInArea = geocoded.every((g) => isInServiceArea(g));
  const warnings: string[] = [];

  if (!allInArea) {
    return {
      error: "One or more addresses are outside the Porterchain GTA service area.",
      code: "OUT_OF_SERVICE_AREA",
    };
  }

  const waypoints = geocoded.map((g) => ({
    latitude: g.latitude,
    longitude: g.longitude,
  }));

  const [route, itemTotals] = await Promise.all([
    calculateRoute(waypoints),
    Promise.resolve(resolveItemTotals(request)),
  ]);

  const vehicleResult = resolveVehicleSelection(request);
  warnings.push(...vehicleResult.warnings);

  if (!vehicleResult.recommended) {
    return {
      error:
        vehicleResult.error ??
        "No supported vehicle fits this shipment. Contact operations for a custom quote.",
      code: "NO_VEHICLE_FIT",
    };
  }

  const recommended = vehicleResult.recommended;
  const alternatives = vehicleResult.alternatives;
  const weightUtilization = vehicleResult.weightUtilization;
  const volumeUtilization = vehicleResult.volumeUtilization;

  const postalCodes = geocoded
    .map((g) => extractFsa(g.address))
    .filter((fsa): fsa is string => fsa != null);

  const pricing = calculateQuotePrice(
    recommended,
    route,
    itemTotals.totalWeightKg,
    stops.length,
    request.urgency,
    request.needHelper,
    postalCodes,
    request.scheduledTime
  );

  if (request.photoCount && request.photoCount > 0) {
    warnings.push("Photos attached — operations may review cargo handling requirements.");
  }

  if (request.cargoLoadType) {
    const loadLabels: Record<string, string> = {
      parcel: "Individual parcel",
      skid: "Skid / pallet",
      ltl: "LTL (less than truckload)",
      ftl: "FTL (full truckload)",
    };
    warnings.push(`Cargo type: ${loadLabels[request.cargoLoadType] ?? request.cargoLoadType}.`);
  }

  const computedInMs = Date.now() - started;

  return {
    quoteId: generateQuoteId(),
    expiresAt: quoteExpiresAt(30),
    currency: "CAD",
    pickup,
    dropoff,
    additionalStops,
    route,
    items: itemTotals,
    recommendedVehicle: recommended,
    alternativeVehicles: alternatives,
    weightUtilization,
    volumeUtilization,
    price: pricing.customerPrice,
    customerPrice: pricing.customerPrice,
    driverPayout: pricing.driverPayout,
    platformMargin: pricing.platformMargin,
    breakdown: pricing.breakdown,
    traffic: pricing.traffic,
    urgency: request.urgency,
    scheduledTime: request.scheduledTime,
    needHelper: request.needHelper,
    computedInMs,
    inServiceArea: allInArea,
    warnings,
  };
}

function validateRequest(request: QuoteRequest) {
  if (!request.pickup?.address?.trim()) {
    throw new Error("Pickup address is required");
  }
  if (!request.dropoff?.address?.trim()) {
    throw new Error("Dropoff address is required");
  }

  if (request.shipmentMode === "whole_vehicle") {
    if (!request.preferredVehicleId || !getVehicleById(request.preferredVehicleId)) {
      throw new Error("Vehicle selection is required");
    }
    return;
  }

  const cargoLoadType = request.cargoLoadType ?? "parcel";
  if (cargoLoadType === "ftl") {
    throw new Error("FTL shipments require vehicle selection");
  }

  if (!request.items?.length) {
    throw new Error("At least one item is required");
  }
  for (const item of request.items) {
    if (item.weight <= 0 || item.length <= 0 || item.width <= 0 || item.height <= 0) {
      throw new Error("Item weight and dimensions must be greater than zero");
    }
  }
}

function resolveItemTotals(request: QuoteRequest): ItemTotals {
  if (request.shipmentMode === "whole_vehicle" && request.preferredVehicleId) {
    const vehicle = getVehicleById(request.preferredVehicleId)!;
    return {
      totalWeightKg: 0,
      totalVolumeM3: 0,
      maxLengthCm: vehicle.maxLengthCm,
      maxWidthCm: vehicle.maxWidthCm,
      maxHeightCm: vehicle.maxHeightCm,
      totalQuantity: 1,
    };
  }

  return calculateItemTotals(request.items);
}

function resolveVehicleSelection(request: QuoteRequest): {
  recommended: VehicleClass | null;
  alternatives: VehicleClass[];
  weightUtilization: number;
  volumeUtilization: number;
  warnings: string[];
  error?: string;
} {
  if (request.shipmentMode === "whole_vehicle" && request.preferredVehicleId) {
    const vehicle = getVehicleById(request.preferredVehicleId);
    if (!vehicle) {
      return {
        recommended: null,
        alternatives: [],
        weightUtilization: 0,
        volumeUtilization: 0,
        warnings: [],
        error: "Invalid vehicle selection",
      };
    }

    return {
      recommended: vehicle,
      alternatives: [],
      weightUtilization: 1,
      volumeUtilization: 1,
      warnings: [
        `Whole-vehicle booking — exclusive use of ${vehicle.name}. Cargo details are not required.`,
      ],
    };
  }

  const { recommended, alternatives, weightUtilization, volumeUtilization, warnings } =
    recommendVehicle(request.items);

  return {
    recommended,
    alternatives,
    weightUtilization,
    volumeUtilization,
    warnings,
  };
}

function timeoutReject(ms: number): Promise<never> {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error("QUOTE_TIMEOUT")), ms);
  });
}

export function isQuoteError(result: QuoteResult | QuoteError): result is QuoteError {
  return "error" in result;
}
