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
  claims: Array<Record<string, unknown>>;
  support_tickets: Array<Record<string, unknown>>;
  documents: Array<Record<string, unknown>>;
  proof_of_delivery: Record<string, unknown>;
  merchant_activity?: Array<Record<string, unknown>>;
  smart: Record<string, unknown>;
};

export const SAVED_FILTERS_KEY = "porterchain.merchant.orders.saved-filters";

async function merchantFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };
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

function qs(filters?: OrderFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const ordersApi = {
  list: (token: string, orgId: string | undefined, filters?: OrderFilters) =>
    merchantFetch<OrderRow[]>(`/v1/merchant/orders${qs(filters)}`, token, { orgId }),

  dashboard: (token: string, orgId?: string) =>
    merchantFetch<OrdersDashboard>("/v1/merchant/orders/dashboard", token, { orgId }),

  detail360: (token: string, orderId: string, orgId?: string) =>
    merchantFetch<OrderDetail>(`/v1/merchant/orders/${orderId}/360`, token, { orgId }),

  tracking: (token: string, orderId: string, orgId?: string) =>
    merchantFetch<LiveTracking>(`/v1/merchant/orders/${orderId}/tracking`, token, {
      orgId,
    }),

  bulk: (token: string, orderIds: string[], action: string, orgId?: string) =>
    merchantFetch<{ results: Array<{ order_id: string; status: string }> }>(
      "/v1/merchant/orders/bulk",
      token,
      { method: "POST", body: JSON.stringify({ order_ids: orderIds, action }), orgId }
    ),
};

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
  return s.replace(/_/g, " ");
}

export function exportOrdersCsv(rows: OrderRow[], filename = "merchant-orders.csv") {
  const headers = [
    "order_number",
    "tracking_number",
    "state",
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
          const v = r[h as keyof OrderRow];
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
  all[name] = filters;
  localStorage.setItem(SAVED_FILTERS_KEY, JSON.stringify(all));
}

export function printOrderLabels(rows: OrderRow[]) {
  const html = `
    <html><head><title>Shipping Labels</title>
    <style>
      body { font-family: sans-serif; }
      .label { border: 2px solid #000; padding: 16px; margin: 12px; page-break-inside: avoid; }
      .tracking { font-size: 24px; font-weight: bold; font-family: monospace; }
    </style></head><body>
    ${rows
      .map(
        (r) => `
      <div class="label">
        <div class="tracking">${r.tracking_number}</div>
        <p><strong>Order:</strong> ${r.order_number}</p>
        <p><strong>From:</strong> ${r.pickup}</p>
        <p><strong>To:</strong> ${r.destination}</p>
        <p><strong>State:</strong> ${formatState(r.state)}</p>
      </div>`
      )
      .join("")}
    </body></html>`;
  const w = window.open("", "_blank");
  if (!w) return;
  w.document.write(html);
  w.document.close();
  w.print();
}
