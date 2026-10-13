/** Pure geo + time helpers for the smart features (no network, no paid APIs). */

export type LatLng = { lat: number; lng: number };

const R = 6_371_000;
const rad = (d: number) => (d * Math.PI) / 180;

/** Great-circle distance in metres. */
export function distanceM(a: LatLng, b: LatLng): number {
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

/** Auto-arrive radius. GPS must be at least this good for the fix to count. */
export const GEOFENCE_M = 100;
export const MAX_FIX_ACCURACY_M = 60;
/** Slower than ~11 km/h — parked or rolling into the driveway, not driving past. */
export const MAX_ARRIVE_SPEED_MPS = 3;

export type Fix = LatLng & { accuracy?: number | null; speed?: number | null };

/** True when a fix is trustworthy and inside the stop's geofence at walking/parking speed. */
export function insideGeofence(fix: Fix, stop: LatLng, radiusM = GEOFENCE_M): boolean {
  if (fix.accuracy != null && fix.accuracy > MAX_FIX_ACCURACY_M) return false;
  if (fix.speed != null && fix.speed > MAX_ARRIVE_SPEED_MPS) return false;
  return distanceM(fix, stop) <= radiusM + Math.min(fix.accuracy ?? 0, 30);
}

/** ETA countdown copy: "4 min", "45 s", "Now", "1 h 05". */
export function etaCountdown(etaAtMs: number, nowMs: number): string {
  const s = Math.round((etaAtMs - nowMs) / 1000);
  if (s <= 15) return "Now";
  if (s < 60) return `${s} s`;
  const m = Math.round(s / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h} h ${String(m % 60).padStart(2, "0")}`;
}

/** Wall-clock arrival "7:42 PM" for the ETA. */
export function clockLabel(atMs: number, locale = "en-CA"): string {
  return new Date(atMs).toLocaleTimeString(locale, { hour: "numeric", minute: "2-digit" });
}

export function distanceLabel(m: number): string {
  return m < 1000 ? `${Math.round(m / 10) * 10} m` : `${(m / 1000).toFixed(m < 10_000 ? 1 : 0)} km`;
}

export function money(cents: number | null | undefined): string {
  if (cents == null) return "—";
  return `$${(cents / 100).toFixed(2)}`;
}
