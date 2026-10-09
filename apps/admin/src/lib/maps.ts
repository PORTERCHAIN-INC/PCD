import { publicEnv } from "@/lib/env";

export function getGoogleMapsApiKey(): string {
  return publicEnv.googleMapsApiKey;
}

export function isGoogleMapsConfigured(): boolean {
  return publicEnv.googleMapsApiKey.length > 0;
}
