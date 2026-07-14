/** Decode Google/OSRM (1e-5) or Valhalla (1e-6) encoded polylines. */
export function decodePolyline(
  encoded: string,
  encoding: "google" | "valhalla" = "google"
): google.maps.LatLngLiteral[] {
  const factor = encoding === "valhalla" ? 1e6 : 1e5;
  const points: google.maps.LatLngLiteral[] = [];
  let index = 0;
  let lat = 0;
  let lng = 0;

  while (index < encoded.length) {
    let shift = 0;
    let result = 0;
    let byte: number;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    const deltaLat = result & 1 ? ~(result >> 1) : result >> 1;
    lat += deltaLat;

    shift = 0;
    result = 0;
    do {
      byte = encoded.charCodeAt(index++) - 63;
      result |= (byte & 0x1f) << shift;
      shift += 5;
    } while (byte >= 0x20);
    const deltaLng = result & 1 ? ~(result >> 1) : result >> 1;
    lng += deltaLng;

    points.push({ lat: lat / factor, lng: lng / factor });
  }
  return points;
}

export function resolveRoutePolylineEncoding(
  route?: { polyline_encoding?: string | null; source?: string | null } | null
): "google" | "valhalla" {
  if (route?.polyline_encoding === "google") return "google";
  if (route?.source === "valhalla") return "valhalla";
  return "google";
}

export function coordsFromAddress(
  addr?: Record<string, unknown> | null
): google.maps.LatLngLiteral | null {
  if (!addr) return null;
  const lat = addr.lat;
  const lng = addr.lng;
  if (typeof lat !== "number" || typeof lng !== "number") return null;
  return { lat, lng };
}

export const GTA_CENTER = { lat: 43.6532, lng: -79.3832 };
