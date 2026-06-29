import { publicEnv } from "@/lib/env";

const API = publicEnv.porterchainApiUrl;

export async function adminFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { role?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    ...(init?.role ? { "X-Admin-Role": init.role } : {}),
  };
  const res = await fetch(`${API}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `API ${res.status}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export type AdminDashboard = {
  todays_revenue_cents: number;
  todays_bookings: number;
  pending_quotes: number;
  pending_merchant_approvals: number;
  drivers_online: number;
  drivers_offline: number;
  orders_waiting_dispatch: number;
  orders_in_transit: number;
  completed_today: number;
  failed_deliveries: number;
  open_claims: number;
  outstanding_invoices_cents: number;
  open_support_tickets: number;
  fleet_health_percent: number;
};

export type PaymentItem = {
  payment_id: string;
  status: string;
  amount_cents: number;
  currency: string;
  stripe_payment_intent_id: string | null;
  stripe_checkout_session_id: string | null;
  receipt_url: string | null;
  failure_reason: string | null;
  retry_count: number;
  created_at: string;
};

export type PricingLineItem = {
  code: string;
  label: string;
  amount_cents: number;
};

export type OrderDetail = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  created_at: string;
  pickup: Record<string, unknown>;
  dropoff: Record<string, unknown>;
  special_instructions: string | null;
  fleetbase_order_id: string | null;
  assigned_driver_id: string | null;
  customer_id: string | null;
  customer_email: string | null;
  customer_phone: string | null;
  booking_number: string | null;
  quote_id: string | null;
  vehicle_class: string | null;
  package_type: string | null;
  weight_kg: number | null;
  dimensions: string | null;
  declared_value_cents: number | null;
  distance_meters: number | null;
  quote_amount_cents: number | null;
  pricing_breakdown: { items?: PricingLineItem[]; summary?: Record<string, unknown> } | null;
  payments: PaymentItem[];
  invoice_number: string | null;
  invoice_amount_cents: number | null;
  invoice_receipt_url: string | null;
  invoice_pdf_url: string | null;
};

export const api = {
  dashboard: (t: string) => adminFetch<AdminDashboard>("/v1/admin/dashboard", t),
  merchants: (t: string, status?: string) =>
    adminFetch<Array<Record<string, unknown>>>(
      `/v1/admin/merchants${status ? `?status=${status}` : ""}`,
      t
    ),
  approveMerchant: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/merchants/${id}/approve`, t, { method: "POST" }),
  suspendMerchant: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/merchants/${id}/suspend`, t, { method: "POST" }),
  drivers: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/drivers", t),
  approveDriver: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/drivers/${id}/approve`, t, { method: "POST" }),
  dispatchQueue: (t: string) =>
    adminFetch<Array<Record<string, unknown>>>("/v1/admin/dispatch/queue", t),
  assignDriver: (t: string, orderId: string, driverId: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/dispatch/orders/${orderId}/assign`, t, {
      method: "POST",
      body: JSON.stringify({ driver_id: driverId }),
    }),
  liveMap: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/map/live", t),
  orders: (t: string, params?: { state?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set("state", params.state);
    if (params?.search) qs.set("search", params.search);
    const q = qs.toString();
    return adminFetch<Array<Record<string, unknown>>>(`/v1/admin/orders${q ? `?${q}` : ""}`, t);
  },
  orderDetail: (t: string, orderId: string) =>
    adminFetch<OrderDetail>(`/v1/admin/orders/${orderId}`, t),
  orderTimeline: (t: string, orderId: string) =>
    adminFetch<Array<Record<string, unknown>>>(`/v1/admin/orders/${orderId}/timeline`, t),
  claims: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/claims", t),
  tariffs: (t: string) =>
    adminFetch<Array<Record<string, unknown>>>("/v1/admin/pricing/tariffs", t),
  financeSummary: (t: string) => adminFetch<Record<string, number>>("/v1/admin/finance/summary", t),
  tickets: (t: string) =>
    adminFetch<Array<Record<string, unknown>>>("/v1/admin/support/tickets", t),
  reports: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/reports/summary", t),
  staff: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/settings/staff", t),
  systemConfig: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/settings/config", t),
  fleetbaseSso: (t: string) =>
    adminFetch<{ console_url: string; sso_token: string; expires_in: number }>(
      "/v1/auth/sso/fleetbase",
      t,
      {
        method: "POST",
      }
    ),
};
