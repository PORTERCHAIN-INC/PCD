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
  on_time_percent: number | null;
  delivery_success_percent: number | null;
  payment_terms: string;
  pending_dispatch?: number;
  outstanding_invoices_cents?: number;
  account_balance_cents?: number;
  performance_charts: DashboardPerformanceCharts;
  recent_deliveries: DashboardDelivery[];
  recent_activity: DashboardActivity[];
  notifications: DashboardNotification[];
  latest_invoice?: DashboardInvoiceLink | null;
  completeness?: {
    complete: boolean;
    missing: string[];
    missing_labels: string[];
    can_edit: boolean;
  } | null;
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
  is_sandbox?: boolean;
  created_at: string;
}

export interface AddressPayload {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
  postal?: string;
}

export interface BookPackagePayload {
  id?: string;
  name?: string;
  sku?: string;
  quantity?: number;
  weight_kg?: number;
  length_cm?: number;
  width_cm?: number;
  height_cm?: number;
  dimensions?: string;
  notes?: string;
  package_type?: string;
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
  site_access_notes?: string;
  requires_liftgate?: boolean;
  otp_required?: boolean;
  custodian_name?: string;
  specimen_id?: string;
  seal_number?: string;
  requires_cold_chain?: boolean;
  temperature_min_c?: number;
  temperature_max_c?: number;
  delivery_window_start?: string;
  delivery_window_end?: string;
  pickup_window_start?: string;
  pickup_window_end?: string;
  packages?: BookPackagePayload[];
  internal_reference?: string;
  purchase_order_number?: string;
  cost_centre?: string;
  recipient_id?: string;
  consignee_email?: string;
  saved_pickup_id?: string;
  template_id?: string;
  is_sandbox?: boolean;
}

export interface MerchantCoverage {
  service_area: string;
  service_area_note: string;
  delivery_zones: Array<{ code: string; name: string }>;
  assigned_vehicles: Array<{ id: string; label: string }>;
  assigned_vehicle_ids: string[];
  coverage_note: string;
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
  coverage?: MerchantCoverage | null;
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
  delivery_success_percent: number | null;
  on_time_percent?: number | null;
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
    "X-Porterchain-Portal": "merchant",
  };
  // M-26: select merchant membership when the user has multiple seats.
  if (init?.orgId) {
    headers["X-Merchant-Id"] = init.orgId;
  }
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join("; ")
          : `API error ${response.status}`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export type MerchantSession = {
  merchant_id: string;
  company_name: string;
  role: string;
  role_label?: string;
  modules: string[];
  user_email: string;
  status?: string;
  status_label?: string;
  logo_url?: string | null;
  coverage?: MerchantCoverage | null;
};

export type MerchantMembership = {
  merchant_id: string;
  company_name: string;
  status: string;
  status_label?: string;
  role: string;
  role_label?: string;
  /** False for suspended or closed companies — listed, but cannot be opened. */
  can_open?: boolean;
  is_current: boolean;
};

export function getMerchantSession(token: string, orgId?: string) {
  return merchantFetch<MerchantSession>("/v1/merchant/session", token, { orgId });
}

export async function getMerchantMemberships(token: string, orgId?: string) {
  const data = await merchantFetch<{ memberships: MerchantMembership[] }>(
    "/v1/merchant/memberships",
    token,
    { orgId }
  );
  return data.memberships ?? [];
}

export function getDashboard(token: string, orgId?: string) {
  return merchantFetch<MerchantDashboard>("/v1/merchant/dashboard", token, { orgId });
}

export function cancelOrder(token: string, orderId: string, orgId?: string) {
  return merchantFetch<MerchantOrder>(`/v1/merchant/orders/${orderId}/cancel`, token, {
    method: "POST",
    orgId,
  });
}

export type BulkUploadWarning = {
  code: "duplicate_file" | "rows_already_imported" | string;
  message: string;
  prior_job_id?: string;
  prior_status?: string;
  prior_filename?: string;
  prior_uploaded_at?: string | null;
  count?: number;
};

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
    warnings?: BulkUploadWarning[];
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

export interface RouteImportJob {
  schema_version: string;
  job_id: string;
  status: string;
  source?: string | null;
  vehicle_class?: string | null;
  scheduled_at?: string | null;
  mapping: Array<Record<string, unknown>>;
  headers?: string[];
  mapping_profile_id?: string | null;
  mapping_profile_name?: string | null;
  optimized?: boolean;
  optimize_status?: "idle" | "pending" | "ready" | "error" | string;
  geocode?: "pending" | "ready" | string;
  stops: Array<Record<string, unknown>>;
  quote: {
    amount_cents?: number;
    subtotal_cents?: number;
    tax_cents?: number;
    currency?: string;
    distance_meters?: number | null;
    routing_source?: string | null;
    vehicle_class?: string;
    total_drops?: number;
    line_items?: Array<{ code: string; label: string; amount_cents: number }>;
  } | null;
  route_geometry?: {
    polyline?: string | null;
    distance_meters?: number;
    duration_seconds?: number;
    source?: string;
    leg_count?: number;
  } | null;
  route_explanation?: string | null;
  errors: Array<Record<string, unknown>>;
  order_ids: string[];
  order_id?: string | null;
  order_state?: string | null;
  assigned_driver_id?: string | null;
  parcel_amendable?: boolean;
  filename?: string | null;
  total_rows: number;
  valid_rows: number;
  error_rows: number;
}

export function uploadRouteImport(
  token: string,
  file: File,
  opts: {
    vehicleClass: string;
    scheduledAt?: string;
    orgId?: string;
    requiresLiftgate?: boolean;
    siteAccessNotes?: string;
    mappingProfileId?: string;
  }
) {
  const form = new FormData();
  form.append("file", file);
  form.append("vehicle_class", opts.vehicleClass);
  if (opts.scheduledAt) form.append("scheduled_at", opts.scheduledAt);
  if (opts.requiresLiftgate) form.append("requires_liftgate", "true");
  if (opts.siteAccessNotes) form.append("site_access_notes", opts.siteAccessNotes);
  if (opts.mappingProfileId) form.append("mapping_profile_id", opts.mappingProfileId);
  return merchantFetch<RouteImportJob>("/v1/merchant/route-imports/upload", token, {
    method: "POST",
    body: form,
    orgId: opts.orgId,
  });
}

export interface RouteListItem {
  job_id: string;
  status: string;
  created_at: string;
  created_on: string;
  scheduled_at?: string | null;
  scheduled_on?: string | null;
  vehicle_class?: string | null;
  construction_site: boolean;
  internal_reference?: string | null;
  stop_count: number;
  label: string;
  amount_cents?: number | null;
  order_id?: string | null;
}

export function listRouteImports(
  token: string,
  opts: {
    date?: string;
    construction?: boolean;
    vehicleClass?: string;
    status?: string;
    search?: string;
    orgId?: string;
  }
) {
  const params = new URLSearchParams();
  if (opts.date) params.set("date", opts.date);
  if (opts.construction) params.set("construction", "true");
  if (opts.vehicleClass) params.set("vehicle_class", opts.vehicleClass);
  if (opts.status) params.set("status", opts.status);
  if (opts.search) params.set("search", opts.search);
  const query = params.toString();
  return merchantFetch<{
    total: number;
    today: number;
    construction: number;
    routes: RouteListItem[];
  }>(`/v1/merchant/route-imports${query ? `?${query}` : ""}`, token, { orgId: opts.orgId });
}

export function createRouteImport(token: string, payload: object, orgId?: string) {
  return merchantFetch<RouteImportJob>("/v1/merchant/route-imports", token, {
    method: "POST",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function getRouteImport(token: string, jobId: string, orgId?: string) {
  return merchantFetch<RouteImportJob>(`/v1/merchant/route-imports/${jobId}`, token, { orgId });
}

export function confirmRouteImport(token: string, jobId: string, orgId?: string) {
  return merchantFetch<RouteImportJob>(`/v1/merchant/route-imports/${jobId}/confirm`, token, {
    method: "POST",
    orgId,
  });
}

export function patchRouteImportStop(
  token: string,
  jobId: string,
  index: number,
  patch: Record<string, unknown>,
  orgId?: string
) {
  return merchantFetch<RouteImportJob>(
    `/v1/merchant/route-imports/${jobId}/stops/${index}`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(patch),
      orgId,
    }
  );
}

export function patchRouteImportMapping(
  token: string,
  jobId: string,
  mapping: Array<Record<string, unknown>>,
  orgId?: string
) {
  return merchantFetch<RouteImportJob>(`/v1/merchant/route-imports/${jobId}/mapping`, token, {
    method: "PATCH",
    body: JSON.stringify({ mapping }),
    orgId,
  });
}

export function optimizeRouteImport(token: string, jobId: string, orgId?: string) {
  return merchantFetch<RouteImportJob>(`/v1/merchant/route-imports/${jobId}/optimize`, token, {
    method: "POST",
    orgId,
  });
}

export type RouteImportMappingProfile = {
  id: string;
  name: string;
  headers: string[];
  mapping: Array<Record<string, unknown>>;
  created_at?: string | null;
};

export function listRouteImportMappingProfiles(token: string, orgId?: string) {
  return merchantFetch<RouteImportMappingProfile[]>("/v1/merchant/route-import-profiles", token, {
    orgId,
  });
}

export function saveRouteImportMappingProfile(
  token: string,
  jobId: string,
  name: string,
  orgId?: string
) {
  return merchantFetch<RouteImportMappingProfile>(
    `/v1/merchant/route-imports/${jobId}/mapping-profile`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ name }),
      orgId,
    }
  );
}

export function applyRouteImportMappingProfile(
  token: string,
  jobId: string,
  profileId: string,
  orgId?: string
) {
  return merchantFetch<RouteImportJob>(
    `/v1/merchant/route-imports/${jobId}/mapping-profile/apply`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ profile_id: profileId }),
      orgId,
    }
  );
}

export function patchOrderParcels(
  token: string,
  orderId: string,
  payload: { stops: Array<Record<string, unknown>>; vehicle_class?: string },
  orgId?: string
) {
  return merchantFetch<{
    order_id: string;
    state: string;
    amount_cents: number;
    quote: RouteImportJob["quote"];
    stops: Array<Record<string, unknown>>;
    parcel_amendable: boolean;
  }>(`/v1/merchant/orders/${orderId}/parcels`, token, {
    method: "PATCH",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function updateProfile(token: string, payload: Partial<MerchantProfile>, orgId?: string) {
  return merchantFetch<MerchantProfile>("/v1/merchant/profile", token, {
    method: "PATCH",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function inviteTeamMember(token: string, email: string, role: string, orgId?: string) {
  return merchantFetch<TeamMember>("/v1/merchant/team/seats", token, {
    method: "POST",
    body: JSON.stringify({ email, role }),
    orgId,
  });
}

export function removeTeamMember(token: string, userId: string, orgId?: string) {
  return merchantFetch<void>(`/v1/merchant/team/${userId}`, token, { method: "DELETE", orgId });
}

export function revokeApiKey(token: string, keyId: string, orgId?: string) {
  return merchantFetch<void>(`/v1/merchant/api-keys/${keyId}`, token, { method: "DELETE", orgId });
}

export interface RoutePricingStatus {
  opted_in: boolean;
  opted_in_at: string | null;
  dismissed_at: string | null;
  show_banner: boolean;
  summary: string;
  examples: Array<{
    from_fsa: string;
    to_fsa: string;
    old_cents: number;
    new_cents: number;
    route_km: number | null;
  }>;
}

export function getRoutePricing(token: string, orgId?: string) {
  return merchantFetch<RoutePricingStatus>("/v1/merchant/pricing/route-pricing", token, { orgId });
}

export function setRoutePricing(
  token: string,
  action: "opt_in" | "opt_out" | "dismiss",
  orgId?: string
) {
  return merchantFetch<RoutePricingStatus>("/v1/merchant/pricing/route-pricing", token, {
    orgId,
    method: "POST",
    body: JSON.stringify({ action }),
  });
}
