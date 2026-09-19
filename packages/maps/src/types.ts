/** Structured address from Google Places (booking / quoting). */
export interface BookingAddress {
  formatted: string;
  placeId?: string;
  lat?: number;
  lng?: number;
  postal?: string;
}
