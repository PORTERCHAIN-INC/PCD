import { publicEnv } from "./env";

export const API_BASE = publicEnv.porterchainApiUrl;

export interface CustomerDashboard {
  active_order: {
    order_id: string;
    tracking_number: string;
    state: string;
  } | null;
  orders: Array<{ order_id: string; tracking_number: string; state: string }>;
  invoices: Array<{ invoice_id: string; invoice_number: string; amount_cents: number; currency: string }>;
  payments: Array<{ payment_id: string; status: string; amount_cents: number; currency: string }>;
}

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
};
