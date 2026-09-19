import { isOntarioPostal, postalFromAddress } from "./ontario";
import type {
  Parcel,
  RouteImportCreatePayload,
  RouteImportPackagePayload,
  RouteJob,
  RouteStop,
} from "./types";
import { convertToCm, convertToKg, formatParcelSpec, serializeParcelsForLegacyAPI } from "./units";

export interface RouteValidation {
  ok: boolean;
  errors: string[];
}

export function validateRouteJob(job: RouteJob): RouteValidation {
  const errors: string[] = [];
  if (!job.pickupLocation.formattedAddress.trim()) {
    errors.push("Pickup address is required");
  }
  if (job.stops.length === 0) {
    errors.push("Add at least one delivery stop");
  }
  job.stops.forEach((stop, index) => {
    const label = `Stop ${index + 1}`;
    if (!stop.formattedAddress.trim()) errors.push(`${label}: address is required`);
    if (!stop.customerName.trim()) errors.push(`${label}: customer name is required`);
    if (!isOntarioPostal(postalFromAddress(stop.formattedAddress, stop.postalCode))) {
      errors.push(`${label}: postal code must be an Ontario code (FSA K, L, M, N, or P)`);
    }
    if (stop.parcels.length === 0) errors.push(`${label}: add at least one parcel`);
    stop.parcels.forEach((parcel, parcelIndex) => {
      const parcelLabel = `${label} parcel ${parcelIndex + 1}`;
      if (!Number.isFinite(parcel.weight) || parcel.weight <= 0) {
        errors.push(`${parcelLabel}: weight must be greater than 0`);
      }
      for (const [name, value] of [
        ["length", parcel.length],
        ["width", parcel.width],
        ["height", parcel.height],
      ] as const) {
        if (!Number.isFinite(value) || value < 0) {
          errors.push(`${parcelLabel}: ${name} must be a non-negative number`);
        }
      }
    });
  });
  return { ok: errors.length === 0, errors };
}

function siteAccessNotes(job: RouteJob): string | undefined {
  const notes = job.siteAccessNotes?.trim();
  if (job.constructionSite) {
    return ["Construction site", notes].filter(Boolean).join(". ");
  }
  return notes || undefined;
}

function toIsoDateTime(value: string | undefined): string | undefined {
  if (!value) return undefined;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return undefined;
  return date.toISOString();
}

export function packagePayload(parcel: Parcel): RouteImportPackagePayload {
  return {
    id: parcel.id,
    name: parcel.name?.trim() || parcel.sku || "Parcel",
    sku: parcel.sku,
    quantity: 1,
    weight_kg: convertToKg(parcel.weight, parcel.weightUnit),
    length_cm: convertToCm(parcel.length, parcel.dimensionsUnit),
    width_cm: convertToCm(parcel.width, parcel.dimensionsUnit),
    height_cm: convertToCm(parcel.height, parcel.dimensionsUnit),
    dimensions: formatParcelSpec(parcel),
  };
}

function stopPayload(stop: RouteStop, sequence: number): RouteImportCreatePayload["stops"][number] {
  return {
    sequence,
    stop_type: "drop",
    address: stop.formattedAddress.trim(),
    postal: postalFromAddress(stop.formattedAddress, stop.postalCode) || undefined,
    lat: stop.latitude,
    lng: stop.longitude,
    contact_name: stop.customerName.trim(),
    contact_phone: stop.customerPhone?.trim() || undefined,
    contact_email: stop.customerEmail?.trim() || undefined,
    notes: stop.deliveryNotes?.trim() || undefined,
    packages: stop.parcels.map(packagePayload),
  };
}

export function toRouteImportPayload(job: RouteJob): RouteImportCreatePayload {
  const parcels = job.stops.flatMap((stop) => stop.parcels);
  const legacy = serializeParcelsForLegacyAPI(parcels);
  const pickup = job.pickupLocation;

  return {
    schema_version: "route_import.v1",
    source: "portal",
    vehicle_class: job.assignedVehicleClass,
    scheduled_at: toIsoDateTime(job.scheduledAt),
    package_type: "looseParcel",
    internal_reference: job.internalReference?.trim() || undefined,
    weight_kg: legacy.weight_kg,
    dimensions: legacy.dimensions,
    requires_liftgate: Boolean(job.constructionSite || job.requiresLiftgate),
    site_access_notes: siteAccessNotes(job),
    stops: [
      {
        sequence: 1,
        stop_type: "pickup",
        address: pickup.formattedAddress.trim(),
        unit: pickup.unit?.trim() || undefined,
        postal: pickup.postalCode?.trim() || undefined,
        lat: pickup.latitude,
        lng: pickup.longitude,
        contact_name: pickup.contactName?.trim() || undefined,
        contact_phone: pickup.contactPhone?.trim() || undefined,
      },
      ...job.stops.map((stop, index) => stopPayload(stop, index + 2)),
    ],
  };
}
