import {
  DimensionUnit,
  MerchantVehicleClass,
  WeightUnit,
  type Parcel,
  type PickupLocation,
  type RouteStop,
} from "./types.ts";
import { canonicalizeCapacityClassId } from "../capacity-catalog";
import { withVolumetricWeight } from "./units.ts";

/** Columns match the route planner form. Repeat sequence to add another parcel to the same stop. */
export const ROUTE_CSV_COLUMNS = [
  "sequence",
  "stop_type",
  "address",
  "unit",
  "postal",
  "contact_name",
  "contact_phone",
  "contact_email",
  "notes",
  "sku",
  "length",
  "width",
  "height",
  "dimensions_unit",
  "weight",
  "weight_unit",
  "vehicle_class",
  "construction_site",
  "site_access",
  "internal_reference",
  "scheduled_at",
] as const;

const SAMPLE = [
  ROUTE_CSV_COLUMNS.join(","),
  [
    "1",
    "pickup",
    '"100 King St W, Toronto, ON M5X 1A9"',
    "1200",
    "M5X 1A9",
    "Warehouse Desk",
    "4165550100",
    "",
    "",
    "",
    "0",
    "0",
    "0",
    "cm",
    "0",
    "kg",
    "cargo_van",
    "no",
    "",
    "PO-100",
    "",
  ].join(","),
  [
    "2",
    "drop",
    '"200 Bay St, Toronto, ON M5J 2J2"',
    "",
    "M5J 2J2",
    "Receiver A",
    "4165550101",
    "a@example.com",
    "Dock 4",
    "BOX-A",
    "12",
    "12",
    "12",
    "in",
    "5",
    "lbs",
    "",
    "yes",
    "Gate code 441",
    "",
    "",
  ].join(","),
  [
    "2",
    "drop",
    '"200 Bay St, Toronto, ON M5J 2J2"',
    "",
    "M5J 2J2",
    "Receiver A",
    "",
    "",
    "",
    "BOX-B",
    "24",
    "12",
    "12",
    "in",
    "15",
    "lbs",
    "",
    "",
    "",
    "",
    "",
  ].join(","),
].join("\n");

export function routeCsvTemplate(): string {
  return SAMPLE;
}

export interface ParsedRouteCsv {
  pickup: PickupLocation;
  stops: RouteStop[];
  vehicleClass?: string;
  constructionSite: boolean;
  siteAccessNotes: string;
  internalReference: string;
  scheduledAt: string;
}

function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let cell = "";
  let quoted = false;
  const source = text.replace(/^\uFEFF/, "");
  for (let i = 0; i < source.length; i += 1) {
    const char = source[i];
    const next = source[i + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        cell += '"';
        i += 1;
      } else if (char === '"') {
        quoted = false;
      } else {
        cell += char;
      }
      continue;
    }
    if (char === '"') {
      quoted = true;
    } else if (char === ",") {
      row.push(cell.trim());
      cell = "";
    } else if (char === "\n") {
      row.push(cell.trim());
      if (row.some((value) => value)) rows.push(row);
      row = [];
      cell = "";
    } else if (char !== "\r") {
      cell += char;
    }
  }
  row.push(cell.trim());
  if (row.some((value) => value)) rows.push(row);
  return rows;
}

function headerIndex(headers: string[]): Map<string, number> {
  const map = new Map<string, number>();
  headers.forEach((header, index) => map.set(header.trim().toLowerCase(), index));
  return map;
}

function cell(row: string[], index: Map<string, number>, name: string): string {
  const at = index.get(name);
  if (at == null) return "";
  return row[at] ?? "";
}

function asNumber(value: string): number {
  if (!value) return 0;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function dimensionUnit(value: string): Parcel["dimensionsUnit"] {
  const unit = value.trim().toLowerCase();
  if (unit === "in" || unit === "inch" || unit === "inches") return DimensionUnit.IN;
  if (unit === "ft" || unit === "feet") return DimensionUnit.FT;
  return DimensionUnit.CM;
}

function weightUnit(value: string): Parcel["weightUnit"] {
  const unit = value.trim().toLowerCase();
  if (unit === "lb" || unit === "lbs" || unit === "pound" || unit === "pounds")
    return WeightUnit.LBS;
  return WeightUnit.KG;
}

function isYes(value: string): boolean {
  return ["1", "y", "yes", "true"].includes(value.trim().toLowerCase());
}

function newId(prefix: string, n: number): string {
  return `${prefix}-${n}`;
}

export type RouteCsvError = { row?: number; error: string; message: string };

export function parseRouteCsv(
  text: string
): { ok: true; route: ParsedRouteCsv } | { ok: false; errors: RouteCsvError[] } {
  const rows = parseCsv(text);
  if (rows.length < 2) {
    return {
      ok: false,
      errors: [
        {
          row: 1,
          error: "missing_columns",
          message: "This file needs a header row and at least one pickup and one drop.",
        },
      ],
    };
  }

  const missing = ROUTE_CSV_COLUMNS.filter((column) => !headerIndex(rows[0]).has(column));
  if (missing.length > 0) {
    return {
      ok: false,
      errors: [
        {
          row: 1,
          error: `missing_columns:${missing.join(",")}`,
          message: `Missing required columns: ${missing.join(", ")}`,
        },
      ],
    };
  }

  const columns = headerIndex(rows[0]);
  const grouped = new Map<string, string[][]>();
  const order: string[] = [];
  for (const row of rows.slice(1)) {
    const sequence = cell(row, columns, "sequence") || String(order.length + 1);
    if (!grouped.has(sequence)) {
      grouped.set(sequence, []);
      order.push(sequence);
    }
    grouped.get(sequence)?.push(row);
  }

  let pickup: PickupLocation | null = null;
  const stops: RouteStop[] = [];
  let vehicleClass = "";
  let constructionSite = false;
  let siteAccessNotes = "";
  let internalReference = "";
  let scheduledAt = "";
  let parcelCounter = 1;

  for (const sequence of order) {
    const group = grouped.get(sequence) ?? [];
    const first = group[0];
    if (!first) continue;
    const stopType = cell(first, columns, "stop_type").toLowerCase();
    const address = cell(first, columns, "address");
    if (!vehicleClass) vehicleClass = cell(first, columns, "vehicle_class");
    if (group.some((row) => isYes(cell(row, columns, "construction_site"))))
      constructionSite = true;
    if (!siteAccessNotes) siteAccessNotes = cell(first, columns, "site_access");
    if (!internalReference) internalReference = cell(first, columns, "internal_reference");
    if (!scheduledAt) scheduledAt = cell(first, columns, "scheduled_at");

    if (stopType === "pickup" || stopType === "pick" || stopType === "pu") {
      pickup = {
        formattedAddress: address,
        unit: cell(first, columns, "unit") || undefined,
        postalCode: cell(first, columns, "postal") || undefined,
        contactName: cell(first, columns, "contact_name") || undefined,
        contactPhone: cell(first, columns, "contact_phone") || undefined,
      };
      continue;
    }

    const parcels: Parcel[] = group.map((row) =>
      withVolumetricWeight({
        id: newId("parcel", parcelCounter++),
        sku: cell(row, columns, "sku") || undefined,
        name: cell(row, columns, "sku") || "Parcel",
        length: asNumber(cell(row, columns, "length")),
        width: asNumber(cell(row, columns, "width")),
        height: asNumber(cell(row, columns, "height")),
        dimensionsUnit: dimensionUnit(cell(row, columns, "dimensions_unit")),
        weight: asNumber(cell(row, columns, "weight")),
        weightUnit: weightUnit(cell(row, columns, "weight_unit")),
      })
    );

    stops.push({
      id: newId("stop", stops.length + 1),
      stopSequence: stops.length + 1,
      formattedAddress: address,
      postalCode: cell(first, columns, "postal"),
      customerName: cell(first, columns, "contact_name"),
      customerPhone: cell(first, columns, "contact_phone") || undefined,
      customerEmail: cell(first, columns, "contact_email") || undefined,
      deliveryNotes: cell(first, columns, "notes") || undefined,
      parcels: parcels.length > 0 ? parcels : [],
    });
  }

  if (!pickup?.formattedAddress) {
    return {
      ok: false,
      errors: [
        { row: 2, error: "missing_pickup", message: "This file must include one pickup row." },
      ],
    };
  }
  if (stops.length === 0) {
    return {
      ok: false,
      errors: [
        { row: 2, error: "missing_drop", message: "This file must include at least one drop row." },
      ],
    };
  }

  const knownVehicles = new Set<string>(Object.values(MerchantVehicleClass));
  const resolved = canonicalizeCapacityClassId(vehicleClass);
  return {
    ok: true,
    route: {
      pickup,
      stops,
      vehicleClass: knownVehicles.has(resolved) ? (resolved as MerchantVehicleClass) : undefined,
      constructionSite,
      siteAccessNotes,
      internalReference,
      scheduledAt,
    },
  };
}
