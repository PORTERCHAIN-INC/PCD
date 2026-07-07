import { formatCoordinates } from "./geocode";
import type { Coordinates, RouteResult } from "./types";

const OSRM_TIMEOUT_MS = 2000;
const VALHALLA_TIMEOUT_MS = 15000;

export async function calculateRoute(waypoints: Coordinates[]): Promise<RouteResult> {
  if (waypoints.length < 2) {
    throw new Error("At least pickup and dropoff are required");
  }

  const engine = (process.env.ROUTING_ENGINE ?? "osrm").toLowerCase();

  if (engine === "valhalla") {
    const valhallaResult = await calculateValhallaRoute(waypoints);
    if (valhallaResult) {
      return valhallaResult;
    }
  }

  return calculateOsrmRoute(waypoints);
}

async function calculateValhallaRoute(waypoints: Coordinates[]): Promise<RouteResult | null> {
  const baseUrl = (
    process.env.VALHALLA_BASE_URL ??
    process.env.VALHALLA_BASE_URI ??
    "http://localhost:8002"
  ).replace(/\/$/, "");

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), VALHALLA_TIMEOUT_MS);

  try {
    const res = await fetch(`${baseUrl}/route`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        locations: waypoints.map((point) => ({
          lat: point.latitude,
          lon: point.longitude,
        })),
        costing: "auto",
      }),
      signal: controller.signal,
      cache: "no-store",
    });

    if (!res.ok) {
      return null;
    }

    const data = await res.json();
    const summary = data.trip?.summary;

    if (!summary) {
      return null;
    }

    // Valhalla returns length in kilometers and time in seconds (not meters).
    const distanceKm = summary.length;
    const durationSeconds = summary.time;

    return {
      distanceMeters: distanceKm * 1000,
      durationSeconds,
      distanceKm: round2(distanceKm),
      durationMinutes: Math.ceil(durationSeconds / 60),
    };
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function calculateOsrmRoute(waypoints: Coordinates[]): Promise<RouteResult> {
  const osrmHost = process.env.OSRM_HOST ?? "https://router.project-osrm.org";
  const coords = waypoints.map(formatCoordinates).join(";");
  const url = `${osrmHost}/route/v1/driving/${coords}?overview=false&steps=false`;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), OSRM_TIMEOUT_MS);

  try {
    const res = await fetch(url, { signal: controller.signal });
    const data = await res.json();

    if (data.code !== "Ok" || !data.routes?.[0]) {
      return estimateRoute(waypoints);
    }

    const route = data.routes[0];
    const distanceMeters = route.distance;
    const durationSeconds = route.duration;

    return {
      distanceMeters,
      durationSeconds,
      distanceKm: round2(distanceMeters / 1000),
      durationMinutes: Math.ceil(durationSeconds / 60),
    };
  } catch {
    return estimateRoute(waypoints);
  } finally {
    clearTimeout(timer);
  }
}

function estimateRoute(waypoints: Coordinates[]): RouteResult {
  let totalMeters = 0;
  for (let i = 1; i < waypoints.length; i++) {
    totalMeters += haversineMeters(waypoints[i - 1], waypoints[i]);
  }
  const roadFactor = 1.35;
  const distanceMeters = totalMeters * roadFactor;
  const durationSeconds = (distanceMeters / 1000 / 40) * 3600;

  return {
    distanceMeters,
    durationSeconds,
    distanceKm: round2(distanceMeters / 1000),
    durationMinutes: Math.ceil(durationSeconds / 60),
  };
}

function haversineMeters(a: Coordinates, b: Coordinates): number {
  const R = 6371000;
  const dLat = toRad(b.latitude - a.latitude);
  const dLng = toRad(b.longitude - a.longitude);
  const lat1 = toRad(a.latitude);
  const lat2 = toRad(b.latitude);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function toRad(deg: number) {
  return (deg * Math.PI) / 180;
}

function round2(n: number) {
  return Math.round(n * 100) / 100;
}
