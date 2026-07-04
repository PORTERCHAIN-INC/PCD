import { publicEnv } from "@/lib/env";

export type { BookingAddress } from "@porterchain/maps/types";
export {
  GTA_LOCATION_BIAS,
  GTA_MAP_BOUNDS,
  applyBookingAutocompleteStyles,
  isGoogleMapsConfigured,
  placeDetailsToBookingAddress,
} from "@porterchain/maps";

export function getGoogleMapsApiKey(): string {
  return publicEnv.googleMapsApiKey;
}
