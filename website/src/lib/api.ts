import { getPorterchainApiBase } from "@/lib/api-base";

const API_BASE = getPorterchainApiBase();

export interface AddressPayload {
  formatted?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
  place_id?: string;
  lat?: number;
  lng?: number;
}

export interface OrderResult {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: AddressPayload;
  dropoff: AddressPayload;
  booking_number?: string | null;
  invoice_number?: string | null;
  company_name?: string | null;
  logo_url?: string | null;
  tracking_page_message?: string | null;
}

export interface TrackingEta {
  source?: string;
  duration_seconds?: number;
  distance_meters?: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
}

export interface OrderLiveTracking {
  order_id: string;
  tracking_number: string;
  state: string;
  fleetbase_order_id?: string | null;
  live_tracking?: {
    pickup?: AddressPayload;
    dropoff?: AddressPayload;
    driver_location?: { lat: number; lng: number; source?: string; recorded_at?: string };
    optimized_route?: { polyline?: string; source?: string };
    eta?: TrackingEta | null;
    delivery_status?: {
      order_state?: string;
      label?: string;
      in_transit?: boolean;
      delivered?: boolean;
    };
    last_updated?: string;
    branding?: {
      company_name?: string | null;
      logo_url?: string | null;
      tracking_page_message?: string | null;
    } | null;
  } | null;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

/** Public guest tracking only — retail book/quote lives on the customer portal. */
export function getOrderByTracking(trackingNumber: string) {
  return apiFetch<OrderResult>(`/v1/orders/${trackingNumber}`);
}

export function getOrderLiveTracking(trackingNumber: string) {
  return apiFetch<OrderLiveTracking>(`/v1/orders/${trackingNumber}/tracking`);
}
