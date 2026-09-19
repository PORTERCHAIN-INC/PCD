import { apiBaseUrl, fetchTimeoutMs } from "./config";

async function fetchWithTimeout(url: string, init: RequestInit = {}): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), fetchTimeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

export type Address = {
  formatted?: string;
};

export type OrderResult = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  pickup?: Address;
  dropoff?: Address;
  tracking_page_message?: string | null;
};

export type OrderLiveTracking = {
  order_id: string;
  tracking_number: string;
  state: string;
  live_tracking?: {
    delivery_status?: {
      order_state?: string;
      label?: string;
      in_transit?: boolean;
      delivered?: boolean;
    };
    eta?: { label?: string; arrives_at?: string } | null;
  } | null;
};

export async function probeApi(): Promise<boolean> {
  try {
    const res = await fetchWithTimeout(`${apiBaseUrl}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

async function publicFetch<T>(path: string): Promise<T> {
  const res = await fetchWithTimeout(`${apiBaseUrl}${path}`, {
    headers: { Accept: "application/json" },
  });
  const text = await res.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      body = text;
    }
  }
  if (!res.ok) {
    throw new Error(res.status === 404 ? "Shipment not found" : `http_${res.status}`);
  }
  return body as T;
}

export function getOrderByTracking(trackingNumber: string): Promise<OrderResult> {
  return publicFetch(`/v1/orders/${encodeURIComponent(trackingNumber)}`);
}

export function getOrderLiveTracking(trackingNumber: string): Promise<OrderLiveTracking> {
  return publicFetch(`/v1/orders/${encodeURIComponent(trackingNumber)}/tracking`);
}
