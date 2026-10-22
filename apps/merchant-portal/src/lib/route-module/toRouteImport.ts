import { normalizeDeliveryOptions } from "@porterchain/types/delivery-options";
import { isOntarioPostal, postalFromAddress } from "./ontario.ts";
import type {
  Parcel,
  RouteImportCreatePayload,
  RouteImportPackagePayload,
  RouteJob,
  RouteStop,
} from "./types.ts";
import {
  convertToCm,
  convertToKg,
  formatParcelSpec,
  serializeParcelsForLegacyAPI,
} from "./units.ts";

export interface RouteValidation {
  ok: boolean;
  errors: string[];
  /** Not blocking: e.g. a stop without a map pin (the server geocodes the address). */
  warnings: string[];
}

/** Text from a field that may be missing on imported / saved / older data. */
export function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function coordIssue(lat: unknown, lng: unknown): "missing" | "invalid" | null {
  if (lat == null && lng == null) return "missing";
  const la = typeof lat === "number" ? lat : Number.NaN;
  const ln = typeof lng === "number" ? lng : Number.NaN;
  if (!Number.isFinite(la) || !Number.isFinite(ln)) return "invalid";
  if (Math.abs(la) > 90 || Math.abs(ln) > 180 || (la === 0 && ln === 0)) return "invalid";
  return null;
}

/**
 * Every problem with the planned route, in words the merchant can act on. Never throws:
 * a pickup, stop or parcel with missing fields (CSV, saved address, Shopify, older drafts)
 * becomes a validation message instead of crashing the planner.
 */
export function validateRouteJob(job: Partial<RouteJob> | null | undefined): RouteValidation {
  const errors: string[] = [];
  const warnings: string[] = [];
  const pickup = (job?.pickupLocation ?? {}) as Partial<RouteJob["pickupLocation"]>;
  if (!text(pickup.formattedAddress)) {
    errors.push("Pickup address is required");
  } else {
    const issue = coordIssue(pickup.latitude, pickup.longitude);
    if (issue === "invalid") {
      errors.push(
        "Pickup: the map location is invalid. Pick the address again from the suggestions"
      );
    } else if (issue === "missing") {
      warnings.push("Pickup: no map pin yet. Pick the address from the suggestions to be exact");
    }
  }
  const stops = Array.isArray(job?.stops) ? job.stops : [];
  if (stops.length === 0) {
    errors.push("Add at least one delivery stop");
  }
  stops.forEach((raw, index) => {
    const label = `Stop ${index + 1}`;
    const stop = (raw ?? {}) as Partial<RouteStop>;
    const address = text(stop.formattedAddress);
    if (!address) errors.push(`${label}: address is required`);
    if (!text(stop.customerName)) errors.push(`${label}: customer name is required`);
    if (!isOntarioPostal(postalFromAddress(address, text(stop.postalCode)))) {
      errors.push(`${label}: postal code must be an Ontario code (FSA K, L, M, N, or P)`);
    }
    if (address) {
      const issue = coordIssue(stop.latitude, stop.longitude);
      if (issue === "invalid") {
        errors.push(
          `${label}: the map location is invalid. Pick the address again from the suggestions`
        );
      } else if (issue === "missing") {
        warnings.push(
          `${label}: no map pin yet. Pick the address from the suggestions to be exact`
        );
      }
    }
    const parcels = Array.isArray(stop.parcels) ? stop.parcels : [];
    if (parcels.length === 0) errors.push(`${label}: add at least one parcel`);
    parcels.forEach((rawParcel, parcelIndex) => {
      const parcelLabel = `${label} parcel ${parcelIndex + 1}`;
      const parcel = (rawParcel ?? {}) as Partial<Parcel>;
      if (!Number.isFinite(parcel.weight) || (parcel.weight as number) <= 0) {
        errors.push(`${parcelLabel}: weight must be greater than 0`);
      }
      for (const [name, value] of [
        ["length", parcel.length],
        ["width", parcel.width],
        ["height", parcel.height],
      ] as const) {
        if (!Number.isFinite(value) || (value as number) < 0) {
          errors.push(`${parcelLabel}: ${name} must be a non-negative number`);
        }
      }
    });
  });
  return { ok: errors.length === 0, errors, warnings };
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

/** item_key per line: a box marked "same item as above" joins the previous line's item. */
export function itemKeys(parcels: Parcel[]): (string | undefined)[] {
  const out: (string | undefined)[] = [];
  parcels.forEach((p, i) => {
    if (i > 0 && p.sameItemAsPrevious) {
      const prev = out[i - 1] ?? `item-${parcels[i - 1].id}`;
      out[i - 1] = prev;
      out.push(prev);
    } else {
      out.push(undefined);
    }
  });
  return out;
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
    address: text(stop.formattedAddress),
    postal: postalFromAddress(text(stop.formattedAddress), stop.postalCode) || undefined,
    lat: stop.latitude,
    lng: stop.longitude,
    contact_name: text(stop.customerName),
    contact_phone: stop.customerPhone?.trim() || undefined,
    contact_email: stop.customerEmail?.trim() || undefined,
    notes: stop.deliveryNotes?.trim() || undefined,
    delivery_options: normalizeDeliveryOptions(stop.deliveryOptions),
    packages: (stop.parcels ?? []).map(packagePayload),
  };
}

export function toRouteImportPayload(job: RouteJob): RouteImportCreatePayload {
  const parcels = job.stops.flatMap((stop) => stop.parcels ?? []);
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
        address: text(pickup.formattedAddress),
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
