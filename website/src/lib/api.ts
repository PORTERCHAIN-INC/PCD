import type {
  DeliveryInstructions,
  DeliveryManageOptions,
  TrackingExperience,
} from "@porterchain/types";
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
  return apiFetch<OrderResult>(`/v1/orders/${trackingNumber}`, { cache: "no-store" });
}

export function getOrderLiveTracking(trackingNumber: string) {
  return apiFetch<OrderLiveTracking>(`/v1/orders/${trackingNumber}/tracking`, {
    cache: "no-store",
  });
}

/** Branded recipient view (enhanced: false unless the merchant turned it on). */
export function getOrderExperience(trackingNumber: string, manageToken?: string | null) {
  return apiFetch<TrackingExperience>(
    `/v1/orders/${encodeURIComponent(trackingNumber)}/experience`,
    {
      cache: "no-store",
      headers: manageToken ? { "X-Manage-Token": manageToken } : undefined,
    }
  );
}

export interface ManageApiError extends Error {
  code: string | null;
  status: number;
}

async function manageFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    referrerPolicy: "no-referrer",
    headers: {
      "Content-Type": "application/json",
      "X-Manage-Token": token,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { code?: string; message?: string } | string;
    };
    const detail = body.detail;
    const err = new Error(
      typeof detail === "string" ? detail : detail?.message || `API error ${response.status}`
    ) as ManageApiError;
    err.code = typeof detail === "object" && detail ? (detail.code ?? null) : null;
    err.status = response.status;
    throw err;
  }
  return response.json() as Promise<T>;
}

export function getDeliveryManageOptions(trackingNumber: string, token: string) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}`,
    token
  );
}

export function postDeliverySchedule(trackingNumber: string, token: string, windowCode: string) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}/schedule`,
    token,
    { method: "POST", body: JSON.stringify({ window_code: windowCode }) }
  );
}

export function postDeliveryInstructions(
  trackingNumber: string,
  token: string,
  instructions: DeliveryInstructions
) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}/instructions`,
    token,
    { method: "POST", body: JSON.stringify(instructions) }
  );
}
