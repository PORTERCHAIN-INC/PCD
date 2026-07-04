import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export interface DashboardChartPoint {
  label: string;
  value: number;
}

export interface DashboardPerformanceCharts {
  daily_orders: DashboardChartPoint[];
  daily_spend_cents: DashboardChartPoint[];
  orders_by_state: Array<{ state: string; count: number }>;
}

export interface DashboardDelivery {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  dropoff?: string | null;
  delivered_at: string;
}

export interface DashboardActivity {
  id: string;
  kind: string;
  title: string;
  detail?: string | null;
  occurred_at: string;
}

export interface DashboardNotification {
  id: string;
  title: string;
  body: string;
  category: string;
  priority: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface DashboardInvoiceLink {
  invoice_id: string;
  invoice_number: string;
  pdf_url?: string | null;
  stripe_receipt_url?: string | null;
}

export interface MerchantDashboard {
  todays_orders: number;
  awaiting_pickup: number;
  in_transit: number;
  delivered_today: number;
  monthly_orders: number;
  monthly_spend_cents: number;
  outstanding_balance_cents: number;
  invoices_due: number;
  open_claims: number;
  open_support_tickets: number;
  on_time_percent: number;
  delivery_success_percent: number;
  payment_terms: string;
  pending_dispatch?: number;
  outstanding_invoices_cents?: number;
  account_balance_cents?: number;
  performance_charts: DashboardPerformanceCharts;
  recent_deliveries: DashboardDelivery[];
  recent_activity: DashboardActivity[];
  notifications: DashboardNotification[];
  latest_invoice?: DashboardInvoiceLink | null;
}

export interface MerchantOrder {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: { formatted?: string };
  dropoff: { formatted?: string };
  internal_reference?: string | null;
  purchase_order_number?: string | null;
  fleetbase_order_id?: string | null;
  created_at: string;
}

export interface AddressPayload {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
}

export interface BookDeliveryPayload {
  pickup: AddressPayload;
  dropoff: AddressPayload;
  additional_stops?: AddressPayload[];
  vehicle_class?: string;
  package_type?: string;
  weight_kg?: number;
  dimensions?: string;
  scheduled_at: string;
  schedule_mode?: string;
  special_instructions?: string;
  internal_reference?: string;
  purchase_order_number?: string;
  cost_centre?: string;
  recipient_id?: string;
  saved_pickup_id?: string;
  template_id?: string;
}

export interface MerchantProfile {
  id: string;
  status: string;
  company_name: string;
  legal_name?: string | null;
  email: string;
  phone?: string | null;
  payment_terms: string;
  hst_number?: string | null;
  business_number?: string | null;
  billing_address?: Record<string, unknown> | null;
  preferred_vehicles?: string[] | null;
  delivery_zones?: string[] | null;
}

export interface TeamMember {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export interface ApiKeyRecord {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  environment: string;
  rate_limit_per_minute: number;
  is_active: boolean;
  created_at: string;
  secret?: string;
}

export interface InvoiceItem {
  invoice_id: string;
  invoice_number: string;
  order_id: string;
  amount_cents: number;
  currency: string;
  created_at: string;
  stripe_receipt_url?: string | null;
}

export interface ReportSummary {
  monthly_orders: number;
  monthly_spend_cents: number;
  delivery_success_percent: number;
  average_delivery_minutes: number | null;
  top_routes: Array<{ route: string; count: number }>;
  invoice_summary_cents: number;
}

export interface BillingStatement {
  payment_terms: string;
  outstanding_balance_cents: number;
  monthly_orders: number;
  monthly_spend_cents: number;
}

async function merchantFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string; role?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export function getDashboard(token: string, orgId?: string) {
  return merchantFetch<MerchantDashboard>("/v1/merchant/dashboard", token, { orgId });
}

export function listOrders(
  token: string,
  orgId?: string,
  params?: { state?: string; search?: string }
) {
  const qs = new URLSearchParams();
  if (params?.state) qs.set("state", params.state);
  if (params?.search) qs.set("search", params.search);
  const q = qs.toString();
  return merchantFetch<MerchantOrder[]>(`/v1/merchant/orders${q ? `?${q}` : ""}`, token, { orgId });
}

export function getOrder(token: string, orderId: string, orgId?: string) {
  return merchantFetch<MerchantOrder>(`/v1/merchant/orders/${orderId}`, token, { orgId });
}

export function trackOrder(token: string, tracking: string, orgId?: string) {
  return merchantFetch<{ order: MerchantOrder; timeline: Array<Record<string, unknown>> }>(
    `/v1/merchant/track/${encodeURIComponent(tracking)}`,
    token,
    { orgId }
  );
}

export function createBooking(token: string, payload: BookDeliveryPayload, orgId?: string) {
  return merchantFetch<MerchantOrder>("/v1/merchant/bookings", token, {
    method: "POST",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function cancelOrder(token: string, orderId: string, orgId?: string) {
  return merchantFetch<MerchantOrder>(`/v1/merchant/orders/${orderId}/cancel`, token, {
    method: "POST",
    orgId,
  });
}

export function duplicateOrder(token: string, orderId: string, orgId?: string) {
  return merchantFetch<MerchantOrder>(`/v1/merchant/orders/${orderId}/duplicate`, token, {
    method: "POST",
    orgId,
  });
}

export function uploadBulkCsv(token: string, file: File, orgId?: string) {
  const form = new FormData();
  form.append("file", file);
  return merchantFetch<{
    job_id: string;
    status: string;
    total_rows: number;
    valid_rows: number;
    error_rows: number;
    duplicate_rows: number;
    preview: Array<Record<string, unknown>>;
    errors: Array<Record<string, unknown>>;
  }>("/v1/merchant/bulk/upload", token, { method: "POST", body: form, orgId });
}

export function confirmBulk(token: string, jobId: string, orgId?: string) {
  return merchantFetch<{ job_id: string; status: string }>(
    `/v1/merchant/bulk/${jobId}/confirm`,
    token,
    {
      method: "POST",
      orgId,
    }
  );
}

export function getProfile(token: string, orgId?: string) {
  return merchantFetch<MerchantProfile>("/v1/merchant/profile", token, { orgId });
}

export function updateProfile(token: string, payload: Partial<MerchantProfile>, orgId?: string) {
  return merchantFetch<MerchantProfile>("/v1/merchant/profile", token, {
    method: "PATCH",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function listTeam(token: string, orgId?: string) {
  return merchantFetch<TeamMember[]>("/v1/merchant/team", token, { orgId });
}

export function inviteTeamMember(token: string, email: string, role: string, orgId?: string) {
  return merchantFetch<TeamMember>("/v1/merchant/team/invite", token, {
    method: "POST",
    body: JSON.stringify({ email, role }),
    orgId,
  });
}

export function removeTeamMember(token: string, userId: string, orgId?: string) {
  return merchantFetch<void>(`/v1/merchant/team/${userId}`, token, { method: "DELETE", orgId });
}

export function listApiKeys(token: string, orgId?: string) {
  return merchantFetch<ApiKeyRecord[]>("/v1/merchant/api-keys", token, { orgId });
}

export function createApiKey(
  token: string,
  payload: { name: string; scopes?: string[]; environment?: string },
  orgId?: string
) {
  return merchantFetch<ApiKeyRecord>("/v1/merchant/api-keys", token, {
    method: "POST",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function revokeApiKey(token: string, keyId: string, orgId?: string) {
  return merchantFetch<void>(`/v1/merchant/api-keys/${keyId}`, token, { method: "DELETE", orgId });
}

export function getBillingStatement(token: string, orgId?: string) {
  return merchantFetch<BillingStatement>("/v1/merchant/billing/statement", token, { orgId });
}

export function listInvoices(token: string, orgId?: string) {
  return merchantFetch<InvoiceItem[]>("/v1/merchant/billing/invoices", token, { orgId });
}

export function getReports(token: string, orgId?: string) {
  return merchantFetch<ReportSummary>("/v1/merchant/reports/summary", token, { orgId });
}
