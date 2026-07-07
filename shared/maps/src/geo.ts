import type { LatLng, MapRegion } from "./types";
import type { MapCoord, ReplayFrame } from "./session";

/** Decode Google / OSRM encoded polyline (precision 5). */
export function decodePolyline(encoded: string, precision = 5): LatLng[] {
  const points: LatLng[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;
  const factor = 10 ** precision;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lat += result & 1 ? ~(result >> 1) : result >> 1;

    shift = 0;
    result = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    lng += result & 1 ? ~(result >> 1) : result >> 1;

    points.push({ latitude: lat / factor, longitude: lng / factor });
  }
  return points;
}

/** Valhalla shape strings use precision 6. */
export function decodeValhallaPolyline(encoded: string): LatLng[] {
  return decodePolyline(encoded, 6);
}

export function decodeRoutePolyline(polyline: string, source?: string): LatLng[] {
  if (!polyline) return [];
  if (source === "valhalla") return decodeValhallaPolyline(polyline);
  return decodePolyline(polyline, 5);
}

export function coordsFromAddress(addr?: Record<string, unknown> | null): LatLng | null {
  if (!addr) return null;
  const lat = addr.lat;
  const lng = addr.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  return { latitude: lat, longitude: lng };
}

export function toLatLng(coord?: MapCoord | null): LatLng | null {
  if (!coord || coord.lat == null || coord.lng == null) return null;
  return { latitude: coord.lat, longitude: coord.lng };
}

export function replayToLatLng(frames: ReplayFrame[]): LatLng[] {
  return frames.map((f) => ({ latitude: f.lat, longitude: f.lng }));
}

export function fitRegion(points: LatLng[], padding = 0.02): MapRegion {
  if (points.length === 0) {
    return { latitude: 43.6532, longitude: -79.3832, latitudeDelta: 0.08, longitudeDelta: 0.08 };
  }
  let minLat = points[0].latitude;
  let maxLat = points[0].latitude;
  let minLng = points[0].longitude;
  let maxLng = points[0].longitude;
  for (const p of points.slice(1)) {
    minLat = Math.min(minLat, p.latitude);
    maxLat = Math.max(maxLat, p.latitude);
    minLng = Math.min(minLng, p.longitude);
    maxLng = Math.max(maxLng, p.longitude);
  }
  const latitude = (minLat + maxLat) / 2;
  const longitude = (minLng + maxLng) / 2;
  const latitudeDelta = Math.max((maxLat - minLat) * 1.4 + padding, 0.02);
  const longitudeDelta = Math.max((maxLng - minLng) * 1.4 + padding, 0.02);
  return { latitude, longitude, latitudeDelta, longitudeDelta };
}

export function formatEta(seconds?: number): string {
  if (!seconds) return "—";
  if (seconds < 60) return "< 1 min";
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function formatDistance(meters?: number): string {
  if (meters == null) return "—";
  if (meters < 1000) return `${Math.round(meters)} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}
