import { publicEnv, isGoogleMapsConfigured as isMapsConfigured } from "@/lib/env";

/** Structured address from Google Places (booking / quoting). */
export interface BookingAddress {
  formatted: string;
  placeId?: string;
  lat?: number;
  lng?: number;
}

export function getGoogleMapsApiKey(): string {
  return publicEnv.googleMapsApiKey;
}

export function isGoogleMapsConfigured(): boolean {
  return isMapsConfigured();
}

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

/** Match booking widget pill inputs (Places API New official CSS properties). */
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
    'var(--font-inter), "Inter", system-ui, -apple-system, sans-serif'
  );
  style.setProperty("font-size", "1rem");
  style.setProperty("color", "#0a1628");
  style.setProperty("transition", "border-color 0.2s, box-shadow 0.2s");
}

export async function placeDetailsToBookingAddress(
  place: google.maps.places.Place
): Promise<BookingAddress | null> {
  await place.fetchFields({
    fields: ["formattedAddress", "displayName", "location", "id"],
  });

  const formatted =
    place.formattedAddress?.trim() || place.displayName?.trim() || "";

  if (!formatted) return null;

  const location = place.location;

  return {
    formatted,
    placeId: place.id,
    lat: location?.lat(),
    lng: location?.lng(),
  };
}
