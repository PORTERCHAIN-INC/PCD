import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type TrackingEta = {
  source?: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
};

export type TrackingRoute = {
  source?: string;
  duration_seconds: number;
  distance_meters: number;
  polyline?: string;
};

export type LiveTracking = {
  order_id: string;
  tracking_number: string;
  order_number?: string;
  state: string;
  display_state?: string;
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
  public_track_url?: string | null;
  is_sandbox?: boolean;
  branding?: {
    company_name?: string | null;
    logo_url?: string | null;
    tracking_page_message?: string | null;
  } | null;
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
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  const response = await fetch(`${API_BASE}${path}`, { ...rest, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    if (isAmbiguousDetail(detail)) {
      throw new AmbiguousTrackingError(detail.message, detail.choices);
    }
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : `API error ${response.status}`;
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

/** One PO covering several drops — the dispatcher picks which one to track (BK). */
export type TrackingChoice = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  dropoff?: string | null;
  scheduled_at?: string | null;
};

export class AmbiguousTrackingError extends Error {
  readonly choices: TrackingChoice[];

  constructor(message: string, choices: TrackingChoice[]) {
    super(message);
    this.name = "AmbiguousTrackingError";
    this.choices = choices;
  }
}

function isAmbiguousDetail(
  detail: unknown
): detail is { message: string; choices: TrackingChoice[] } {
  return (
    typeof detail === "object" &&
    detail !== null &&
    "choices" in detail &&
    Array.isArray((detail as { choices: unknown }).choices)
  );
}

export function publicTrackUrl(trackingNumber: string, fromApi?: string | null): string {
  if (fromApi) return fromApi;
  return `${publicEnv.websiteUrl}/track/${encodeURIComponent(trackingNumber)}`;
}

export async function copyPublicTrackUrl(
  trackingNumber: string,
  fromApi?: string | null
): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(publicTrackUrl(trackingNumber, fromApi));
    return true;
  } catch {
    return false;
  }
}

export const trackingApi = {
  dashboard: (token: string, orgId?: string) =>
    trackingFetch<TrackingDashboard>("/v1/merchant/tracking/dashboard", token, { orgId }),

  byOrderId: (token: string, orderId: string, orgId?: string) =>
    trackingFetch<LiveTracking>(`/v1/merchant/orders/${orderId}/tracking`, token, { orgId }),

  byTrackingNumber: (token: string, trackingNumber: string, orgId?: string) =>
    trackingFetch<{
      order: Record<string, unknown>;
      timeline: Array<Record<string, unknown>>;
      live_tracking: LiveTracking;
    }>(`/v1/merchant/track/${encodeURIComponent(trackingNumber)}`, token, { orgId }),
};

export function formatEta(seconds?: number) {
  if (!seconds) return "—";
  if (seconds < 60) return "< 1 min";
  const m = Math.floor(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  return `${h}h ${m % 60}m`;
}
