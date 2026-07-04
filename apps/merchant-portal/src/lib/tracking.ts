import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type TrackingEta = {
  source: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
};

export type TrackingRoute = {
  source: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
};

export type LiveTracking = {
  order_id: string;
  tracking_number: string;
  order_number?: string;
  state: string;
  scheduled_at?: string;
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  driver?: Record<string, unknown> | null;
  vehicle?: Record<string, unknown> | null;
  driver_location?: { lat: number; lng: number } | null;
  eta?: TrackingEta | null;
  optimized_route?: TrackingRoute | null;
  delivery_status?: Record<string, unknown>;
  timeline?: Array<Record<string, unknown>>;
  tracking_history?: Array<Record<string, unknown>>;
  replay?: Array<{ lat: number; lng: number; at?: string; source?: string }>;
  proof_of_delivery?: {
    photos?: Array<Record<string, unknown>>;
    signatures?: Array<Record<string, unknown>>;
    otp?: Array<Record<string, unknown>>;
    complete?: boolean;
  };
  geofences?: Array<Record<string, unknown>>;
  notifications?: Array<Record<string, unknown>>;
  last_updated?: string;
};

export type TrackingDashboard = {
  active_count: number;
  orders: Array<Record<string, unknown>>;
  geofences: Array<Record<string, unknown>>;
  updated_at: string;
};

async function trackingFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const trackingApi = {
  dashboard: (token: string, orgId?: string) =>
    trackingFetch<TrackingDashboard>("/v1/merchant/tracking/dashboard", token, { orgId }),

  byOrderId: (token: string, orderId: string, orgId?: string) =>
    trackingFetch<LiveTracking>(`/v1/merchant/tracking/orders/${orderId}`, token, { orgId }),

  byTrackingNumber: (token: string, trackingNumber: string, orgId?: string) =>
    trackingFetch<{ order: Record<string, unknown>; timeline: Array<Record<string, unknown>>; live_tracking: LiveTracking }>(
      `/v1/merchant/track/${encodeURIComponent(trackingNumber)}`,
      token,
      { orgId }
    ),
};

export function formatEta(seconds?: number) {
  if (!seconds) return "—";
  if (seconds < 60) return "< 1 min";
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}
