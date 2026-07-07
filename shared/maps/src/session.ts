/** Map session geometry from Porterchain API — never computed on client. */

export type MapCoord = { lat: number; lng: number };

export type RouteLeg = {
  source: "osrm" | "valhalla" | string;
  label?: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string | null;
  arrives_at?: string | null;
  eta_label?: string | null;
};

export type MapGeofence = {
  id: string;
  name?: string;
  geofence_type: "pickup" | "dropoff" | "delivery_zone" | "warehouse" | string;
  center: MapCoord;
  radius_m: number;
};

export type ReplayFrame = MapCoord & { at?: string | null; source?: string };

export type HeatmapPoint = MapCoord & { weight?: number };

export type MapEntity = {
  id: string;
  kind: "driver" | "customer" | "merchant" | "warehouse" | "pickup" | "dropoff" | "device";
  coordinate: MapCoord;
  title?: string;
  subtitle?: string;
};

export type RoutingEngines = {
  gps: string;
  eta: string;
  optimized_route: string;
  map_display: string;
};

/** Unified session for EnterpriseMap — populated from API responses only. */
export type EnterpriseMapSession = {
  idle?: boolean;
  order_id?: string | null;
  tracking_number?: string | null;
  state?: string;
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  merchant?: Record<string, unknown> | null;
  warehouse?: Record<string, unknown> | null;
  driver_location?: MapCoord | null;
  customer_location?: MapCoord | null;
  current_location?: MapCoord | null;
  device_location?: MapCoord | null;
  pickup_route?: RouteLeg | null;
  delivery_route?: RouteLeg | null;
  optimized_route?: RouteLeg | null;
  eta?: RouteLeg | null;
  route_polyline?: string | null;
  geofences?: MapGeofence[];
  replay?: ReplayFrame[];
  heatmap?: HeatmapPoint[];
  traffic?: { layer_available: boolean; source: string };
  routing_engines?: Partial<RoutingEngines> & Record<string, string>;
  gps_source?: string | null;
  last_updated?: string | null;
};
