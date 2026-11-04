/**
 * Self-hosted map style for the native map (doc 60 R4): MapLibre Native reads the
 * Protomaps PMTiles archive straight from our tiles host (pmtiles:// protocol).
 * No map vendor and no API key. Same style as the web portals (packages/maps).
 */
import { layers, namedFlavor } from "@protomaps/basemaps";
import type { StyleSpecification } from "@maplibre/maplibre-react-native";

export type LatLng = { latitude: number; longitude: number };

export function tilesBase(): string {
  return (process.env.EXPO_PUBLIC_MAP_TILES_URL || "https://tiles.porterchain.com")
    .trim()
    .replace(/\/+$/, "");
}

export function porterchainNativeStyle(
  scheme: "light" | "dark" = "light",
  base: string = tilesBase()
): StyleSpecification {
  return {
    version: 8,
    glyphs: `${base}/fonts/{fontstack}/{range}.pbf`,
    sprite: `${base}/sprites/v4/${scheme}`,
    sources: {
      protomaps: {
        type: "vector",
        url: `pmtiles://${base}/gta-150km.pmtiles`,
        attribution: "© OpenStreetMap",
      },
    },
    layers: layers("protomaps", namedFlavor(scheme), {
      lang: "en",
    }) as unknown as StyleSpecification["layers"],
  };
}

/** [[west, south], [east, north]]-style bounds as MapLibre wants: [w, s, e, n]. */
export function boundsOf(points: LatLng[]): [number, number, number, number] | null {
  if (points.length === 0) return null;
  let w = Infinity,
    s = Infinity,
    e = -Infinity,
    n = -Infinity;
  for (const p of points) {
    w = Math.min(w, p.longitude);
    e = Math.max(e, p.longitude);
    s = Math.min(s, p.latitude);
    n = Math.max(n, p.latitude);
  }
  // A single point (or identical points): pad ~1 km so the camera can fit it.
  const pad = 0.01;
  if (e - w < pad) {
    w -= pad;
    e += pad;
  }
  if (n - s < pad) {
    s -= pad;
    n += pad;
  }
  return [w, s, e, n];
}
