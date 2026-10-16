/// <reference types="google.maps" />
import type { BookingAddress } from "./types";

/** GTA + southern Ontario bias for Porterchain service area. */
export const GTA_MAP_BOUNDS = {
  south: 43.35,
  west: -80.2,
  north: 44.35,
  east: -78.7,
} as const;

export const GTA_LOCATION_BIAS: google.maps.LatLngBoundsLiteral = {
  south: GTA_MAP_BOUNDS.south,
  west: GTA_MAP_BOUNDS.west,
  north: GTA_MAP_BOUNDS.north,
  east: GTA_MAP_BOUNDS.east,
};

export const GTA_CENTER = { lat: 43.6532, lng: -79.3832 };

export function coordsFromAddress(
  addr?: Record<string, unknown> | null
): google.maps.LatLngLiteral | null {
  if (!addr) return null;
  const lat = addr.lat;
  const lng = addr.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  return { lat, lng };
}

export function resolveGoogleMapsApiKey(explicit?: string): string {
  return (explicit ?? process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY ?? "").trim();
}

export function isGoogleMapsConfigured(apiKey?: string): boolean {
  return resolveGoogleMapsApiKey(apiKey).length > 0;
}

export function applyBookingAutocompleteStyles(
  element: google.maps.places.PlaceAutocompleteElement
) {
  const style = element.style;
  style.setProperty("width", "100%");
  style.setProperty("display", "block");
  style.setProperty("box-sizing", "border-box");
  style.setProperty("color-scheme", "light");
  style.setProperty("background-color", "#ffffff");
  style.setProperty("border", "1px solid transparent");
  style.setProperty("border-radius", "9999px");
  style.setProperty("min-height", "3rem");
  style.setProperty(
    "font-family",
    'Calibri, var(--font-brand), Carlito, Candara, "Segoe UI", Arial, sans-serif'
  );
  style.setProperty("font-size", "1rem");
  style.setProperty("color", "#0a1628");
  style.setProperty("transition", "border-color 0.2s, box-shadow 0.2s");
}

export async function placeDetailsToBookingAddress(
  place: google.maps.places.Place
): Promise<BookingAddress | null> {
  await place.fetchFields({
    fields: ["formattedAddress", "displayName", "location", "id", "addressComponents"],
  });

  const formatted = place.formattedAddress?.trim() || place.displayName?.trim() || "";
  if (!formatted) return null;

  const location = place.location;
  const postal = place.addressComponents?.find((c) => (c.types ?? []).includes("postal_code"));
  return {
    formatted,
    placeId: place.id,
    lat: location?.lat(),
    lng: location?.lng(),
    postal: postal?.shortText || postal?.longText || undefined,
  };
}

/** API base for /v1/geo/* (same default as each portal's API client). */
export function resolveGeoApiBase(explicit?: string): string {
  const raw = (explicit ?? process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "").trim();
  if (raw) return raw.replace(/\/+$/, "");
  return process.env.NODE_ENV === "development"
    ? "http://localhost:8001"
    : "https://api.porterchain.com";
}

export type GeoSuggestion = { id: string; main: string; secondary: string; formatted: string };

export async function fetchGeoSuggestions(
  q: string,
  opts: { apiBase?: string; signal?: AbortSignal } = {}
): Promise<GeoSuggestion[]> {
  const base = resolveGeoApiBase(opts.apiBase);
  const res = await fetch(`${base}/v1/geo/autocomplete?q=${encodeURIComponent(q)}&limit=6`, {
    signal: opts.signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) return [];
  const data = (await res.json()) as { results?: GeoSuggestion[] };
  return data.results ?? [];
}

export async function resolveGeoPlace(
  input: { id?: string; q?: string },
  opts: { apiBase?: string; signal?: AbortSignal } = {}
): Promise<BookingAddress | null> {
  const base = resolveGeoApiBase(opts.apiBase);
  const qs = input.id
    ? `id=${encodeURIComponent(input.id)}`
    : `q=${encodeURIComponent(input.q ?? "")}`;
  const res = await fetch(`${base}/v1/geo/place?${qs}`, {
    signal: opts.signal,
    headers: { Accept: "application/json" },
  });
  if (!res.ok) return null;
  const d = (await res.json()) as Record<string, unknown>;
  const formatted = typeof d.formatted === "string" ? d.formatted : "";
  if (!formatted) return null;
  return {
    formatted,
    placeId: typeof d.placeId === "string" ? d.placeId : input.id,
    lat: typeof d.lat === "number" ? d.lat : undefined,
    lng: typeof d.lng === "number" ? d.lng : undefined,
    postal: typeof d.postal === "string" && d.postal ? d.postal : undefined,
  };
}
