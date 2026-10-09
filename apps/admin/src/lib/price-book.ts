/**
 * Helpers for the super-admin "Price book & driver pay" settings card.
 * The API owns validation and defaults (porterchain_pricing.price_book /
 * driver_pay); these helpers only read and edit the stored JSON.
 */

export type JsonObject = Record<string, unknown>;

/** Values still awaiting a business decision; shown with an EXAMPLE badge. */
export const PRICE_BOOK_PLACEHOLDERS: readonly string[] = [
  "stop_price_cents",
  "parcel_tiers",
  "small_parcel.max_lb",
  "small_parcel.charge_mode",
  "minimum.cents",
  "minimum.mode",
  "retail.fixed_price_cents",
  "retail.included_parcels",
  "retail.extra_parcel_cents",
  "dedicated.unit",
  "dedicated.vehicles",
];

export const DRIVER_PAY_PLACEHOLDERS: readonly string[] = [
  "per_stop_cents",
  "per_pickup_cents",
  "per_route_cents",
  "route_included_stops",
  "route_extra_stop_cents",
  "wave_block.block_cents",
  "wave_block.included_stops",
  "wave_block.extra_stop_cents",
];

export const DRIVER_PAY_MODES = [
  "hourly",
  "per_stop",
  "per_route",
  "wave_block",
  "hybrid",
] as const;

export function asObject(v: unknown): JsonObject {
  return typeof v === "object" && v !== null && !Array.isArray(v) ? (v as JsonObject) : {};
}

export function getPath(obj: unknown, path: string): unknown {
  let cur: unknown = obj;
  for (const part of path.split(".")) {
    if (Array.isArray(cur)) cur = cur[Number(part)];
    else cur = asObject(cur)[part];
    if (cur === undefined) return undefined;
  }
  return cur;
}

/** Immutable set by dotted path; numeric parts index arrays. */
export function setPath<T>(obj: T, path: string, value: unknown): T {
  const [head, ...rest] = path.split(".");
  const key = head ?? "";
  if (Array.isArray(obj)) {
    const copy = [...obj];
    const i = Number(key);
    copy[i] = rest.length ? setPath(copy[i], rest.join("."), value) : value;
    return copy as T;
  }
  const src = asObject(obj);
  return {
    ...src,
    [key]: rest.length ? setPath(src[key], rest.join("."), value) : value,
  } as T;
}

/** True when `path` (or a parent) is still an EXAMPLE value. */
export function isPlaceholder(path: string, placeholders: readonly string[]): boolean {
  return placeholders.some((p) => path === p || path.startsWith(`${p}.`));
}

export function centsToDollars(v: unknown): string {
  const n = Number(v);
  return Number.isFinite(n) ? (n / 100).toFixed(2) : "0.00";
}

export function dollarsToCents(v: string): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.round(n * 100)) : 0;
}

export function wholeNumber(v: string, fallback = 0): number {
  const n = Number(v);
  return Number.isFinite(n) ? Math.max(0, Math.floor(n)) : fallback;
}

export function formatPriceVersion(v: unknown): string | null {
  const ver = Number(asObject(v).version);
  return Number.isFinite(ver) && ver > 0 ? `pv-${ver}` : null;
}
