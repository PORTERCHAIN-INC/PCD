import { publicEnv } from "@/lib/env";

export function getGoogleMapsApiKey(): string {
  return publicEnv.googleMapsApiKey;
}

export function isGoogleMapsConfigured(): boolean {
  return publicEnv.googleMapsApiKey.length > 0;
}

export const GTA_DEFAULT_CENTER = { lat: 43.6532, lng: -79.3832 };
export const GTA_DEFAULT_ZOOM = 11;

export function wsLiveMapUrl(token: string): string {
  const base = publicEnv.porterchainApiUrl.replace(/^http/, "ws");
  return `${base}/v1/admin/operations/live-map/ws?token=${encodeURIComponent(token)}`;
}
