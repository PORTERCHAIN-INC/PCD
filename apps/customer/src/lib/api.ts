import { publicEnv } from "./env";

export const API_BASE = publicEnv.porterchainApiUrl;

export interface CustomerDashboard {
  active_order: {
    order_id: string;
    tracking_number: string;
    state: string;
  } | null;
  orders: Array<{ order_id: string; tracking_number: string; state: string }>;
  invoices: Array<{
    invoice_id: string;
    invoice_number: string;
    amount_cents: number;
    currency: string;
  }>;
  payments: Array<{ payment_id: string; status: string; amount_cents: number; currency: string }>;
}

export interface CancelOrderResult {
  order_id: string;
  tracking_number: string;
  state: string;
  refunded: boolean;
  refund_pending: boolean;
  refund_amount_cents: number;
}

/** Order states in which a customer may self-cancel (mirrors the API guard). */
export const CUSTOMER_CANCELLABLE_STATES = ["BOOKED", "DISPATCH_READY", "DRIVER_ASSIGNED"];

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export const customerApi = {
  dashboard: (token: string) =>
    apiFetch<CustomerDashboard>("/v1/customers/me/dashboard", {
      headers: { Authorization: `Bearer ${token}` },
    }),
  createSupport: (token: string, body: { subject: string; description?: string }) =>
    apiFetch("/v1/customers/me/support", {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify(body),
    }),
  rebook: (token: string, orderId: string) =>
    apiFetch<{ tracking_number: string }>(`/v1/customers/me/rebook/${orderId}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    }),
  // Cancel consumes the standardized {success,data}/{error} envelope.
  cancelOrder: async (token: string, orderId: string): Promise<CancelOrderResult> => {
    const res = await fetch(`${API_BASE}/v1/customers/me/orders/${orderId}/cancel`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const message = body?.error?.message ?? body?.detail ?? "Unable to cancel order";
      throw new Error(typeof message === "string" ? message : "Unable to cancel order");
    }
    return (body?.data ?? body) as CancelOrderResult;
  },
};
