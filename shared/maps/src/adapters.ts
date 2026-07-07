import { coordsFromAddress } from "./geo";
import type { EnterpriseMapSession, MapGeofence } from "./session";

type DriverNavLike = {
  idle?: boolean;
  order_id?: string | null;
  tracking_number?: string | null;
  state?: string;
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  merchant?: Record<string, unknown>;
  warehouse?: Record<string, unknown>;
  driver_location?: { lat: number; lng: number } | null;
  current_location?: { lat: number; lng: number } | null;
  pickup_route?: EnterpriseMapSession["pickup_route"];
  delivery_route?: EnterpriseMapSession["delivery_route"];
  optimized_route?: EnterpriseMapSession["optimized_route"];
  eta?: EnterpriseMapSession["eta"];
  route_polyline?: string | null;
  geofences?: Array<Record<string, unknown>>;
  replay?: Array<{ lat: number; lng: number; at?: string; source?: string }>;
  traffic?: EnterpriseMapSession["traffic"];
  routing_engines?: Record<string, string>;
  gps_source?: string | null;
  last_updated?: string | null;
  customer?: { location?: { lat: number; lng: number } };
};

/** Adapt driver navigation API session → map session (render only). */
export function driverSessionToMapSession(
  session: DriverNavLike,
  deviceLocation?: { lat: number; lng: number } | null
): EnterpriseMapSession {
  const geofences = (session.geofences ?? []).map((g) => {
    const center = g.center as { lat: number; lng: number } | undefined;
    return {
      id: String(g.id ?? ""),
      name: g.name as string | undefined,
      geofence_type: String(g.geofence_type ?? "delivery_zone"),
      center: center ?? { lat: 0, lng: 0 },
      radius_m: typeof g.radius_m === "number" ? g.radius_m : 150,
    } satisfies MapGeofence;
  });

  const replay = (session.replay ?? []).map((f) => ({
    lat: f.lat,
    lng: f.lng,
    at: f.at,
    source: f.source,
  }));

  const heatmap = replay.map((f, i) => ({
    lat: f.lat,
    lng: f.lng,
    weight: 0.5 + (i / Math.max(replay.length, 1)) * 0.5,
  }));

  const dropoffCoord = coordsFromAddress(session.dropoff);

  return {
    idle: session.idle,
    order_id: session.order_id,
    tracking_number: session.tracking_number,
    state: session.state,
    pickup: session.pickup ?? null,
    dropoff: session.dropoff ?? null,
    merchant: session.merchant ?? null,
    warehouse: session.warehouse ?? null,
    driver_location: session.driver_location ?? session.current_location ?? null,
    customer_location:
      session.customer?.location ??
      (dropoffCoord ? { lat: dropoffCoord.latitude, lng: dropoffCoord.longitude } : null),
    current_location: session.current_location ?? null,
    device_location: deviceLocation ?? null,
    pickup_route: session.pickup_route ?? null,
    delivery_route: session.delivery_route ?? null,
    optimized_route: session.optimized_route ?? null,
    eta: session.eta ?? null,
    route_polyline: session.route_polyline ?? null,
    geofences,
    replay,
    heatmap,
    traffic: session.traffic,
    routing_engines: session.routing_engines,
    gps_source: session.gps_source,
    last_updated: session.last_updated,
  };
}

/** Adapt customer live tracking payload → map session. */
export function liveTrackingToMapSession(live: {
  driver_location?: { lat: number; lng: number };
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  eta_minutes?: number;
  status?: string;
  [key: string]: unknown;
}): EnterpriseMapSession {
  const dropoff = coordsFromAddress(live.dropoff);
  return {
    pickup: live.pickup ?? null,
    dropoff: live.dropoff ?? null,
    driver_location: live.driver_location ?? null,
    customer_location: dropoff ? { lat: dropoff.latitude, lng: dropoff.longitude } : null,
    routing_engines: {
      gps: "fleetbase",
      eta: "osrm",
      optimized_route: "valhalla",
      map_display: "google_maps",
    },
    gps_source: "fleetbase",
    state: String(live.status ?? ""),
  };
}
