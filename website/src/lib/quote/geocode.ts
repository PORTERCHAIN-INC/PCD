import type { Coordinates, GeocodedAddress, QuoteAddress } from "./types";

const GEOCODE_TIMEOUT_MS = 2000;

export async function geocodeAddress(address: QuoteAddress): Promise<GeocodedAddress> {
  if (address.latitude != null && address.longitude != null) {
    return {
      address: address.address,
      latitude: address.latitude,
      longitude: address.longitude,
    };
  }

  const googleKey =
    process.env.GOOGLE_MAPS_SERVER_API_KEY ??
    process.env.GOOGLE_MAPS_API_KEY ??
    process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;
  if (googleKey) {
    return geocodeGoogle(address.address, googleKey);
  }

  return geocodeNominatim(address.address);
}

async function geocodeGoogle(address: string, apiKey: string): Promise<GeocodedAddress> {
  const query = encodeURIComponent(`${address}, Ontario, Canada`);
  const url = `https://maps.googleapis.com/maps/api/geocode/json?address=${query}&key=${apiKey}&region=ca`;

  const res = await fetchWithTimeout(url, GEOCODE_TIMEOUT_MS);
  const data = await res.json();

  if (data.status !== "OK" || !data.results?.[0]) {
    throw new Error(`Could not geocode address: ${address}`);
  }

  const result = data.results[0];
  return {
    address: result.formatted_address ?? address,
    latitude: result.geometry.location.lat,
    longitude: result.geometry.location.lng,
  };
}

async function geocodeNominatim(address: string): Promise<GeocodedAddress> {
  const query = encodeURIComponent(`${address}, Ontario, Canada`);
  const url = `https://nominatim.openstreetmap.org/search?q=${query}&format=json&limit=1&countrycodes=ca`;

  const res = await fetchWithTimeout(url, GEOCODE_TIMEOUT_MS, {
    headers: {
      "User-Agent": "PorterchainQuoteEngine/1.0 (https://porterchain.com)",
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    throw new Error(`Could not geocode address: ${address}`);
  }

  const data = await res.json();

  if (!Array.isArray(data) || data.length === 0) {
    throw new Error(`Could not geocode address: ${address}`);
  }

  return {
    address: data[0].display_name ?? address,
    latitude: parseFloat(data[0].lat),
    longitude: parseFloat(data[0].lon),
  };
}

export async function geocodeAddresses(addresses: QuoteAddress[]): Promise<GeocodedAddress[]> {
  return Promise.all(addresses.map((a) => geocodeAddress(a)));
}

async function fetchWithTimeout(
  url: string,
  timeoutMs: number,
  init?: RequestInit
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

export function formatCoordinates(coords: Coordinates): string {
  return `${coords.longitude},${coords.latitude}`;
}
