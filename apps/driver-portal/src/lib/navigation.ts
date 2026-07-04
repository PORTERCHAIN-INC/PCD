export type RouteLeg = {
  source: string;
  label?: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
  arrives_at?: string;
  eta_label?: string;
};

export type DriverNavigationSession = {
  idle?: boolean;
  message?: string;
  order_id: string | null;
  tracking_number: string | null;
  order_number: string | null;
  state: string;
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  pickup_route?: RouteLeg | null;
  delivery_route?: RouteLeg | null;
  optimized_route?: RouteLeg | null;
  eta?: RouteLeg | null;
  route_polyline?: string | null;
  navigation_url?: string | null;
  current_location?: { lat: number; lng: number } | null;
  driver_location?: { lat: number; lng: number } | null;
  gps_source?: string | null;
  delivery_status?: Record<string, unknown>;
  stops?: Array<Record<string, unknown>>;
  timeline?: Array<Record<string, unknown>>;
  replay?: Array<{ lat: number; lng: number; at?: string; source?: string }>;
  geofences?: Array<Record<string, unknown>>;
  traffic?: { layer_available: boolean; source: string };
  offline_maps?: { enabled: boolean; future_ready: boolean; message: string };
  routing_engines?: {
    gps: string;
    eta: string;
    optimized_route: string;
    map_display: string;
  };
  last_updated?: string;
};

export function formatEta(seconds?: number) {
  if (!seconds) return "—";
  if (seconds < 60) return "< 1 min";
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}

export function formatDistance(meters?: number) {
  if (meters == null) return "—";
  if (meters < 1000) return `${meters} m`;
  return `${(meters / 1000).toFixed(1)} km`;
}
