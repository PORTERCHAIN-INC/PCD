import type { Coordinates } from "./types";

const GTA_BOUNDS = {
  minLat: 43.45,
  maxLat: 44.1,
  minLng: -79.85,
  maxLng: -78.9,
};

export function isInServiceArea(coords: Coordinates): boolean {
  return (
    coords.latitude >= GTA_BOUNDS.minLat &&
    coords.latitude <= GTA_BOUNDS.maxLat &&
    coords.longitude >= GTA_BOUNDS.minLng &&
    coords.longitude <= GTA_BOUNDS.maxLng
  );
}

export function generateQuoteId(): string {
  const year = new Date().getFullYear();
  const seq = Math.floor(Math.random() * 900000) + 100000;
  return `PC-${year}-${seq}`;
}

export function quoteExpiresAt(minutes = 30): string {
  return new Date(Date.now() + minutes * 60 * 1000).toISOString();
}
