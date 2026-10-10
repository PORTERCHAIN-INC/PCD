import { API_BASE } from "./api";

export interface MyDelivery {
  tracking_number: string;
  order_number: string;
  state: string;
  active: boolean;
  amount_cents: number;
  currency: string;
  created_at: string | null;
  pickup: string | null;
  dropoff: string | null;
  extra_drops: number;
  rating: number | null;
  receipt_url: string | null;
  receipt_number: string | null;
  can_cancel: boolean;
  track_url: string;
  send_again_url: string | null;
}

export interface MyDeliveries {
  summary: { orders: number; active: number; spent_cents: number };
  orders: MyDelivery[];
}

export interface SavedAddress {
  id: string;
  label: string | null;
  formatted: string;
  postal: string | null;
  saved: boolean;
  use_count: number;
}

export type ProblemKind = "late" | "damaged" | "missing" | "wrong_address" | "return" | "billing" | "other";

async function call<T>(token: string, path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      "X-Porterchain-Portal": "customer",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = body?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || "Something went wrong. Try again.");
  }
  return res.json();
}

export const accountApi = {
  deliveries: (t: string) => call<MyDeliveries>(t, "/v1/customers/me/deliveries"),
  addresses: (t: string) => call<SavedAddress[]>(t, "/v1/customers/me/addresses"),
  suggestions: (t: string, q = "") =>
    call<SavedAddress[]>(t, `/v1/customers/me/address-suggestions?q=${encodeURIComponent(q)}`),
  saveAddress: (t: string, body: { formatted: string; label?: string | null }) =>
    call<SavedAddress>(t, "/v1/customers/me/addresses", { method: "POST", body: JSON.stringify(body) }),
  deleteAddress: (t: string, id: string) =>
    call<{ ok: boolean }>(t, `/v1/customers/me/addresses/${encodeURIComponent(id)}`, { method: "DELETE" }),
  reportProblem: (t: string, tracking: string, kind: ProblemKind, details: string) =>
    call<{ status: string; reply_within_hours: number }>(
      t,
      `/v1/customers/me/orders/${encodeURIComponent(tracking)}/problem`,
      { method: "POST", body: JSON.stringify({ kind, details: details || null }) }
    ),
  preferencesLink: (t: string) => call<{ url: string }>(t, "/v1/customers/me/preferences-link"),
};

export const PROBLEM_LABELS: Record<ProblemKind, string> = {
  late: "Late or missed",
  damaged: "Damaged",
  missing: "Missing item",
  wrong_address: "Wrong place",
  return: "Return to sender",
  billing: "Billing",
  other: "Other",
};

export const STATE_LABEL: Record<string, string> = {
  BOOKED: "Booked",
  DISPATCH_READY: "Finding a driver",
  DRIVER_ASSIGNED: "Driver assigned",
  DRIVER_ACCEPTED: "Driver assigned",
  DRIVER_EN_ROUTE: "Driver on the way",
  AT_PICKUP: "At pickup",
  PICKED_UP: "Picked up",
  IN_TRANSIT: "On the way",
  AT_DESTINATION: "Arriving",
  DELIVERED: "Delivered",
  POD_COMPLETED: "Delivered",
  INVOICED: "Delivered",
  CLOSED: "Delivered",
  CANCELLED: "Cancelled",
  FAILED: "Delivery failed",
  RETURN_TO_SENDER: "Returning",
  REFUNDED: "Refunded",
};
