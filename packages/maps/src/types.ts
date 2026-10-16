/** Structured address from PorterChain geo search (Photon / Nominatim / FSA). */
export interface BookingAddress {
  formatted: string;
  placeId?: string;
  lat?: number;
  lng?: number;
  postal?: string;
}

export interface LatLng {
  lat: number;
  lng: number;
}
