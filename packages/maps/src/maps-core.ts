import type { BookingAddress, LatLng } from "./types";

/** GTA + southern Ontario bias for Porterchain service area. */
export const GTA_MAP_BOUNDS = {
  south: 43.35,
  west: -80.2,
  north: 44.35,
  east: -78.7,
} as const;

export const GTA_CENTER: LatLng = { lat: 43.6532, lng: -79.3832 };

export function coordsFromAddress(addr?: Record<string, unknown> | null): LatLng | null {
  if (!addr) return null;
  const lat = addr.lat;
  const lng = addr.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  return { lat, lng };
}

/** Self-hosted Protomaps tiles (MapLibre). */
export function resolveTilesBase(explicit?: string): string {
  return (explicit ?? process.env.NEXT_PUBLIC_MAP_TILES_URL ?? "https://tiles.porterchain.com")
    .trim()
    .replace(/\/+$/, "");
}

/** Maps are always available now (no API key). Kept for call sites that gate on it. */
export function isMapsConfigured(): boolean {
  return true;
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
