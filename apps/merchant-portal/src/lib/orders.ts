import { orderStateLabel } from "@/lib/catalog";
import { publicEnv } from "@/lib/env";
import type { LiveTracking } from "@/lib/tracking";

const API_BASE = publicEnv.porterchainApiUrl;

export const ORDER_STATES = [
  "BOOKED",
  "DISPATCH_READY",
  "DRIVER_ASSIGNED",
  "DRIVER_ACCEPTED",
  "DRIVER_EN_ROUTE",
  "AT_PICKUP",
  "PICKED_UP",
  "IN_TRANSIT",
  "AT_DESTINATION",
  "DELIVERED",
  "POD_COMPLETED",
  "INVOICED",
  "CLOSED",
  "CANCELLED",
  "FAILED",
  "RETURN_TO_SENDER",
  "DAMAGED",
  "LOST",
  "CLAIM_OPEN",
  "REFUNDED",
] as const;

export type OrderRow = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  booking_number?: string | null;
  driver_id?: string | null;
  driver_name?: string | null;
  vehicle_label?: string | null;
  pickup: string;
  destination: string;
  service_type?: string | null;
  priority: string;
  state: string;
  display_state: string;
  payment_status?: string | null;
  invoice_status: string;
  amount_cents: number;
  currency: string;
  eta?: string | null;
  sla_status: string;
  delay_risk_score: number;
  scheduled_at: string;
  created_at: string;
  updated_at: string;
  purchase_order_number?: string | null;
  cost_centre?: string | null;
  internal_reference?: string | null;
  order_source?: string | null;
  order_source_label?: string | null;
  shopify?: {
    shop_domain?: string | null;
    order_id?: string | null;
    order_name?: string | null;
  } | null;
  is_sandbox?: boolean;
};

export const ORDER_PAGE_SIZE = 50;

export type OrderListPage = {
  items: OrderRow[];
  total: number;
  limit: number;
  offset: number;
};

export type OrderFilters = {
  state?: string;
  payment_status?: string;
  invoice_status?: string;
  driver_id?: string;
  priority?: string;
  service_type?: string;
  city?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  amount_min_cents?: number;
  amount_max_cents?: number;
  /** live (default) | sandbox | all */
  env?: "live" | "sandbox" | "all";
  include_sandbox?: boolean;
  sandbox_only?: boolean;
  limit?: number;
  offset?: number;
};

export type OrdersDashboard = {
  orders_today: number;
  orders_in_progress: number;
  waiting_dispatch: number;
  assigned: number;
  picked_up: number;
  delivered: number;
  failed: number;
  returned: number;
  claims: number;
  open_support_tickets: number;
  revenue_today_cents: number;
  avg_delivery_hours: number;
  avg_pickup_hours: number;
  avg_sla_percent: number;
};

export type OrderDetail = OrderRow & {
  internal_reference?: string | null;
  purchase_order_number?: string | null;
  cost_centre?: string | null;
  special_instructions?: string | null;
  fleetbase_order_id?: string | null;
  customer_phone?: string | null;
  quote_id?: string | null;
  vehicle_class?: string | null;
  package_type?: string | null;
  weight_kg?: number | null;
  dimensions?: string | null;
  declared_value_cents?: number | null;
  distance_meters?: number | null;
  quote_amount_cents?: number | null;
  pricing_breakdown?: Record<string, unknown> | null;
  pickup_detail: Record<string, unknown>;
  dropoff_detail: Record<string, unknown>;
  invoice_number?: string | null;
  invoice_amount_cents?: number | null;
  invoice_receipt_url?: string | null;
  invoice_pdf_url?: string | null;
  driver?: Record<string, unknown> | null;
  vehicle?: Record<string, unknown> | null;
  driver_status?: string | null;
  vehicle_status?: string | null;
  timeline: Array<Record<string, unknown>>;
  tracking?: Record<string, unknown> | null;
  packages: Array<Record<string, unknown>>;
  stops?: Array<Record<string, unknown>>;
  parcel_amendable?: boolean;
  route_import_job_id?: string | null;
  claims: Array<Record<string, unknown>>;
  support_tickets: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  proof_of_delivery: Record<string, unknown>;
  merchant_activity?: Array<Record<string, unknown>>;
  smart?: Record<string, unknown>;
  consignee_email?: string | null;
  cancel_allowed?: boolean;
  cancel_rule?: string | null;
};

export type BulkActionResult = {
  order_id: string;
  tracking_number?: string;
  ok: boolean;
  status: string;
  message: string;
};

export type BulkActionResponse = {
  results: BulkActionResult[];
  ok_count?: number;
  failed_count?: number;
};

export const SAVED_FILTERS_KEY = "porterchain.merchant.orders.saved-filters";

async function merchantFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
    "Content-Type": "application/json",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : `API error ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function qs(filters?: OrderFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  const { env, ...rest } = filters;
  Object.entries(rest).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  if (env === "sandbox") {
    p.set("sandbox_only", "true");
  } else if (env === "all") {
    p.set("include_sandbox", "true");
  }
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const ordersApi = {
  list: (token: string, orgId: string | undefined, filters?: OrderFilters) =>
    merchantFetch<OrderListPage>(`/v1/merchant/orders${qs(filters)}`, token, { orgId }),

  dashboard: (token: string, orgId?: string) =>
    merchantFetch<OrdersDashboard>("/v1/merchant/orders/dashboard", token, { orgId }),

  detail360: (token: string, orderId: string, orgId?: string) =>
    merchantFetch<OrderDetail>(`/v1/merchant/orders/${orderId}/360`, token, { orgId }),

  tracking: (token: string, orderId: string, orgId?: string) =>
    merchantFetch<LiveTracking>(`/v1/merchant/orders/${orderId}/tracking`, token, {
      orgId,
    }),

  bulk: (token: string, orderIds: string[], action: string, orgId?: string) =>
    merchantFetch<BulkActionResponse>("/v1/merchant/orders/bulk", token, {
      method: "POST",
      body: JSON.stringify({ order_ids: orderIds, action }),
      orgId,
    }),

  cancel: (token: string, orderId: string, orgId?: string) =>
    merchantFetch<{ order_id: string; state: string }>(
      `/v1/merchant/orders/${orderId}/cancel`,
      token,
      {
        method: "POST",
        orgId,
      }
    ),

  amendParcels: (
    token: string,
    orderId: string,
    payload: { stops: Array<Record<string, unknown>>; vehicle_class?: string },
    orgId?: string
  ) =>
    merchantFetch<{
      order_id: string;
      state: string;
      amount_cents: number;
      quote: Record<string, unknown> | null;
      stops: Array<Record<string, unknown>>;
      parcel_amendable: boolean;
    }>(`/v1/merchant/orders/${orderId}/parcels`, token, {
      method: "PATCH",
      body: JSON.stringify(payload),
      orgId,
    }),

  compliancePdfPath: (orderId: string) => `/v1/merchant/orders/${orderId}/compliance-dossier.pdf`,

  printPreviewPath: (orderId: string) => `/v1/merchant/orders/${orderId}/print-preview.pdf`,

  labelsPdfPath: (orderId: string) => `/v1/merchant/orders/${orderId}/labels.pdf`,

  labelsBulkPath: () => `/v1/merchant/orders/labels/bulk`,

  pickupManifestPath: (orderIds: string[]) => {
    const p = new URLSearchParams();
    orderIds.forEach((id) => p.append("ids", id));
    return `/v1/merchant/orders/pickup-manifest.pdf?${p.toString()}`;
  },

  /** Every POD photo and the signature, zipped (BR). */
  podBundlePath: (orderId: string) => `/v1/merchant/orders/${orderId}/pod.zip`,

  /** One POD photo or the signature, by the handle the gallery carries (BR). */
  podArtifactPath: (orderId: string, slug: string) =>
    `/v1/merchant/orders/${orderId}/pod/${encodeURIComponent(slug)}`,

  pickupListPath: (orderIds: string[]) => {
    const p = new URLSearchParams();
    orderIds.forEach((id) => p.append("ids", id));
    return `/v1/merchant/orders/pickup-list.pdf?${p.toString()}`;
  },

  emailTracking: (token: string, orderId: string, email?: string, orgId?: string) =>
    merchantFetch<{ sent: boolean; email: string; public_track_url: string | null }>(
      `/v1/merchant/orders/${orderId}/tracking-email`,
      token,
      { method: "POST", body: JSON.stringify({ email: email || null }), orgId }
    ),
};

/** The filename the API chose, when it sent one. */
function filenameFromHeader(header: string | null): string | null {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header ?? "");
  return match ? decodeURIComponent(match[1]).trim() || null : null;
}

/**
 * Save a file the API serves as an attachment.
 *
 * `filename` is the fallback: the API names its own downloads, and for POD the
 * extension is only known server-side once the media type is read.
 */
export async function downloadMerchantFile(
  token: string,
  path: string,
  filename: string,
  orgId?: string,
  init?: RequestInit
) {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
    ...(init?.headers as Record<string, string> | undefined),
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  const response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(
      typeof (body as { detail?: string }).detail === "string"
        ? (body as { detail: string }).detail
        : `Download failed (${response.status})`
    );
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filenameFromHeader(response.headers.get("Content-Disposition")) ?? filename;
  a.click();
  URL.revokeObjectURL(url);
}

export const STATE_STYLES: Record<string, string> = {
  BOOKED: "bg-blue-100 text-blue-800",
  DISPATCH_READY: "bg-indigo-100 text-indigo-800",
  DRIVER_ASSIGNED: "bg-violet-100 text-violet-800",
  IN_TRANSIT: "bg-teal-100 text-teal-800",
  DELIVERED: "bg-green-100 text-green-800",
  POD_COMPLETED: "bg-green-100 text-green-800",
  CANCELLED: "bg-gray-100 text-gray-600",
  FAILED: "bg-red-100 text-red-800",
  CLAIM_OPEN: "bg-amber-100 text-amber-900",
};

export function formatState(s: string) {
  return orderStateLabel(s);
}

export function exportOrdersCsv(rows: OrderRow[], filename = "merchant-orders.csv") {
  const headers = [
    "order_number",
    "tracking_number",
    "purchase_order_number",
    "cost_centre",
    "internal_reference",
    "state",
    "is_sandbox",
    "driver_name",
    "pickup",
    "destination",
    "payment_status",
    "invoice_status",
    "amount_cents",
    "priority",
    "scheduled_at",
    "created_at",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => {
          let v: unknown = r[h as keyof OrderRow];
          if (h === "is_sandbox") v = Boolean(r.is_sandbox);
          const s = v == null ? "" : String(v);
          return s.includes(",") ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function loadSavedFilterNames(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(SAVED_FILTERS_KEY);
    if (!raw) return [];
    return Object.keys(JSON.parse(raw) as Record<string, OrderFilters>);
  } catch {
    return [];
  }
}

export function loadSavedFilter(name: string): OrderFilters | null {
  try {
    const raw = localStorage.getItem(SAVED_FILTERS_KEY);
    if (!raw) return null;
    return (JSON.parse(raw) as Record<string, OrderFilters>)[name] ?? null;
  } catch {
    return null;
  }
}

export function saveFilter(name: string, filters: OrderFilters) {
  const raw = localStorage.getItem(SAVED_FILTERS_KEY);
  const all = raw ? (JSON.parse(raw) as Record<string, OrderFilters>) : {};
  const { limit: _limit, offset: _offset, ...persisted } = filters;
  all[name] = persisted;
  localStorage.setItem(SAVED_FILTERS_KEY, JSON.stringify(all));
}
