/**
 * City / service-area geo coordinates for hyperlocal Service schema (near-me SEO).
 * Approximate municipal centers — not street-level precision.
 */

export type HyperlocalGeo = {
  locality: string;
  region: string;
  latitude: number;
  longitude: number;
};

/** service-area slug → geo (Ontario metros Porterchain serves). */
export const SERVICE_AREA_GEO: Record<string, HyperlocalGeo> = {
  toronto: { locality: "Toronto", region: "ON", latitude: 43.6532, longitude: -79.3832 },
  mississauga: { locality: "Mississauga", region: "ON", latitude: 43.589, longitude: -79.6441 },
  brampton: { locality: "Brampton", region: "ON", latitude: 43.7315, longitude: -79.7624 },
  vaughan: { locality: "Vaughan", region: "ON", latitude: 43.8361, longitude: -79.4983 },
  markham: { locality: "Markham", region: "ON", latitude: 43.8563, longitude: -79.337 },
  oakville: { locality: "Oakville", region: "ON", latitude: 43.4675, longitude: -79.6877 },
  burlington: { locality: "Burlington", region: "ON", latitude: 43.3255, longitude: -79.799 },
  oshawa: { locality: "Oshawa", region: "ON", latitude: 43.8971, longitude: -78.8658 },
  "kitchener-waterloo": {
    locality: "Kitchener",
    region: "ON",
    latitude: 43.4516,
    longitude: -80.4925,
  },
  london: { locality: "London", region: "ON", latitude: 42.9849, longitude: -81.2453 },
  "st-catharines": {
    locality: "St. Catharines",
    region: "ON",
    latitude: 43.1594,
    longitude: -79.2469,
  },
  niagara: { locality: "Niagara Falls", region: "ON", latitude: 43.0896, longitude: -79.0849 },
  cambridge: { locality: "Cambridge", region: "ON", latitude: 43.3616, longitude: -80.3144 },
  guelph: { locality: "Guelph", region: "ON", latitude: 43.5448, longitude: -80.2482 },
  hamilton: { locality: "Hamilton", region: "ON", latitude: 43.2557, longitude: -79.8711 },
  ajax: { locality: "Ajax", region: "ON", latitude: 43.8509, longitude: -79.0204 },
  pickering: { locality: "Pickering", region: "ON", latitude: 43.8384, longitude: -79.0868 },
};

/** city URL slug (e.g. kitchener) → service-area slug for geo lookup. */
export function resolveServiceAreaGeoSlug(cityOrAreaSlug: string): string {
  const map: Record<string, string> = { kitchener: "kitchener-waterloo" };
  return map[cityOrAreaSlug] ?? cityOrAreaSlug;
}

export function getHyperlocalGeo(slug: string): HyperlocalGeo | null {
  const key = resolveServiceAreaGeoSlug(slug);
  return SERVICE_AREA_GEO[key] ?? null;
}
