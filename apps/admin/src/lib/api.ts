import { publicEnv } from "@/lib/env";

const API = publicEnv.porterchainApiUrl;

async function adminFetch<T>(path: string, token: string, init?: RequestInit & { role?: string }): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    ...(init?.role ? { "X-Admin-Role": init.role } : {}),
  };
  const res = await fetch(`${API}${path}`, { ...init, headers: { ...headers, ...(init?.headers as Record<string, string>) } });
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

export const api = {
  dashboard: (t: string) => adminFetch<AdminDashboard>("/v1/admin/dashboard", t),
  crmSummary: (t: string) => adminFetch<Record<string, number>>("/v1/admin/crm/summary", t),
  crmLeads: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/crm/leads", t),
  merchants: (t: string, status?: string) =>
    adminFetch<Array<Record<string, unknown>>>(`/v1/admin/merchants${status ? `?status=${status}` : ""}`, t),
  approveMerchant: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/merchants/${id}/approve`, t, { method: "POST" }),
  suspendMerchant: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/merchants/${id}/suspend`, t, { method: "POST" }),
  drivers: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/drivers", t),
  approveDriver: (t: string, id: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/drivers/${id}/approve`, t, { method: "POST" }),
  dispatchQueue: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/dispatch/queue", t),
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
  orderTimeline: (t: string, orderId: string) =>
    adminFetch<Array<Record<string, unknown>>>(`/v1/admin/orders/${orderId}/timeline`, t),
  claims: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/claims", t),
  tariffs: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/pricing/tariffs", t),
  financeSummary: (t: string) => adminFetch<Record<string, number>>("/v1/admin/finance/summary", t),
  tickets: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/support/tickets", t),
  reports: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/reports/summary", t),
  staff: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/settings/staff", t),
  systemConfig: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/settings/config", t),
  fleetbaseSso: (t: string) =>
    adminFetch<{ console_url: string; sso_token: string; expires_in: number }>("/v1/auth/sso/fleetbase", t, {
      method: "POST",
    }),
};
