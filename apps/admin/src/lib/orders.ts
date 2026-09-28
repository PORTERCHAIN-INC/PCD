import { z } from "zod";
import { adminFetch } from "@/lib/api";

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

const orderRowSchema = z.object({
  order_id: z.string(),
  order_number: z.string(),
  tracking_number: z.string(),
  booking_number: z.string().nullable().optional(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  customer_id: z.string().nullable().optional(),
  customer_email: z.string().nullable().optional(),
  driver_id: z.string().nullable().optional(),
  driver_name: z.string().nullable().optional(),
  vehicle_label: z.string().nullable().optional(),
  pickup: z.string(),
  destination: z.string(),
  service_type: z.string().nullable().optional(),
  priority: z.string(),
  state: z.string(),
  display_state: z.string(),
  payment_status: z.string().nullable().optional(),
  invoice_status: z.string(),
  amount_cents: z.number(),
  currency: z.string(),
  eta: z.string().nullable().optional(),
  sla_status: z.string(),
  fraud_risk_score: z.number(),
  delay_risk_score: z.number(),
  scheduled_at: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  purchase_order_number: z.string().nullable().optional(),
  cost_centre: z.string().nullable().optional(),
  internal_reference: z.string().nullable().optional(),
  order_source: z.string().nullable().optional(),
  order_source_label: z.string().nullable().optional(),
  shopify: z
    .object({
      shop_domain: z.string().nullable().optional(),
      order_id: z.string().nullable().optional(),
      order_name: z.string().nullable().optional(),
      fulfillment_id: z.string().nullable().optional(),
      last_tracking_push_at: z.string().nullable().optional(),
      last_tracking_state: z.string().nullable().optional(),
      last_fulfillment_error: z.string().nullable().optional(),
      held_for_ops: z.boolean().nullable().optional(),
      auto_dispatch: z.boolean().nullable().optional(),
      last_repush_at: z.string().nullable().optional(),
      last_event_status: z.string().nullable().optional(),
      last_event_at: z.string().nullable().optional(),
      order_admin_url: z.string().nullable().optional(),
    })
    .nullable()
    .optional(),
});

export type OrderRow = z.infer<typeof orderRowSchema>;

const paymentSchema = z.object({
  payment_id: z.string(),
  status: z.string(),
  amount_cents: z.number(),
  currency: z.string(),
  stripe_payment_intent_id: z.string().nullable().optional(),
  stripe_checkout_session_id: z.string().nullable().optional(),
  receipt_url: z.string().nullable().optional(),
  failure_reason: z.string().nullable().optional(),
  retry_count: z.number(),
  created_at: z.string(),
});

export const orderDetailSchema = orderRowSchema.extend({
  special_instructions: z.string().nullable().optional(),
  fleetbase_order_id: z.string().nullable().optional(),
  customer_phone: z.string().nullable().optional(),
  booking_id: z.string().nullable().optional(),
  booking_draft_id: z.string().nullable().optional(),
  booking_draft_number: z.string().nullable().optional(),
  quote_id: z.string().nullable().optional(),
  vehicle_class: z.string().nullable().optional(),
  package_type: z.string().nullable().optional(),
  weight_kg: z.number().nullable().optional(),
  dimensions: z.string().nullable().optional(),
  declared_value_cents: z.number().nullable().optional(),
  booking_mode: z.string().nullable().optional(),
  parcels: z.array(z.record(z.string(), z.unknown())).optional(),
  distance_meters: z.number().nullable().optional(),
  quote_amount_cents: z.number().nullable().optional(),
  pricing_breakdown: z.record(z.string(), z.unknown()).nullable().optional(),
  pickup_detail: z.record(z.string(), z.unknown()),
  dropoff_detail: z.record(z.string(), z.unknown()),
  additional_stops: z.array(z.unknown()),
  stops: z.array(z.record(z.string(), z.unknown())).optional(),
  parcel_amendable: z.boolean().optional(),
  route_import_job_id: z.string().nullable().optional(),
  payments: z.array(paymentSchema),
  invoice_number: z.string().nullable().optional(),
  invoice_amount_cents: z.number().nullable().optional(),
  invoice_receipt_url: z.string().nullable().optional(),
  invoice_pdf_url: z.string().nullable().optional(),
  merchant: z.record(z.string(), z.unknown()).nullable().optional(),
  customer_360: z.record(z.string(), z.unknown()).nullable().optional(),
  driver: z.record(z.string(), z.unknown()).nullable().optional(),
  vehicle: z.record(z.string(), z.unknown()).nullable().optional(),
  driver_status: z.string().nullable().optional(),
  vehicle_status: z.string().nullable().optional(),
  parcel_count: z.number().optional(),
  timeline: z.array(z.record(z.string(), z.unknown())),
  tracking: z.record(z.string(), z.unknown()).nullable().optional(),
  packages: z.array(z.record(z.string(), z.unknown())),
  incidents: z.array(z.record(z.string(), z.unknown())),
  claims: z.array(z.record(z.string(), z.unknown())),
  support_tickets: z.array(z.record(z.string(), z.unknown())),
  documents: z.array(z.record(z.string(), z.unknown())),
  proof_of_delivery: z.record(z.string(), z.unknown()),
  domain_events: z.array(z.record(z.string(), z.unknown())),
  audit_log: z.array(z.record(z.string(), z.unknown())),
  internal_notes: z.array(z.record(z.string(), z.unknown())),
  automation: z.array(z.record(z.string(), z.unknown())).optional(),
  communications: z.array(z.record(z.string(), z.unknown())).optional(),
  api_activity: z.array(z.record(z.string(), z.unknown())).optional(),
  duplicates: z.array(z.record(z.string(), z.unknown())),
  smart: z.record(z.string(), z.unknown()),
  status_sync: z.record(z.string(), z.unknown()).optional(),
});

export type OrderDetail = z.infer<typeof orderDetailSchema>;

export type OrderDashboard = {
  orders_today: number;
  orders_in_progress: number;
  waiting_dispatch: number;
  assigned: number;
  picked_up: number;
  delivered: number;
  failed: number;
  returned: number;
  claims: number;
  revenue_today_cents: number;
  avg_delivery_hours: number;
  avg_pickup_hours: number;
  avg_sla_percent: number;
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
  merchant_id?: string;
  driver_id?: string;
  customer_id?: string;
  priority?: string;
  service_type?: string;
  city?: string;
  search?: string;
  date_from?: string;
  date_to?: string;
  /** scheduled = service day in America/Toronto. Omit to keep created-at filtering. */
  date_field?: "scheduled" | "created";
  /** needs_decision | on_the_road | open | done. A specific state replaces this. */
  queue?: string;
  include_carryover?: boolean;
  amount_min_cents?: number;
  amount_max_cents?: number;
  limit?: number;
  offset?: number;
};

const B = "/v1/admin/orders";

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
  list: async (token: string, filters?: OrderFilters) => {
    const raw = await adminFetch<unknown>(`${B}${qs(filters)}`, token);
    return z
      .object({
        items: z.array(orderRowSchema),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
      })
      .parse(raw);
  },
  dashboard: (token: string) => adminFetch<OrderDashboard>(`${B}/dashboard`, token),
  reports: (token: string) => adminFetch<Record<string, unknown>>(`${B}/reports`, token),
  detail: async (token: string, id: string) => {
    const raw = await adminFetch<unknown>(`${B}/${id}`, token);
    return orderDetailSchema.parse(raw);
  },
  tracking: (token: string, id: string) =>
    adminFetch<Record<string, unknown>>(`${B}/${id}/tracking`, token),
  bulk: (token: string, orderIds: string[], action: string, opts?: { driver_id?: string }) =>
    adminFetch<{ results: Array<{ order_id: string; status: string }> }>(`${B}/bulk`, token, {
      method: "POST",
      body: JSON.stringify({ order_ids: orderIds, action, ...opts }),
    }),
  generateInvoice: (token: string, id: string) =>
    adminFetch<{
      order_id: string;
      invoice_id: string;
      invoice_number: string;
      receipt_number: string | null;
      amount_cents: number;
    }>(`${B}/${id}/invoice`, token, { method: "POST" }),
  resendReceipt: (token: string, id: string) =>
    adminFetch<{
      order_id: string;
      invoice_number: string;
      email: string | null;
      receipt_url: string | null;
    }>(`${B}/${id}/resend-receipt`, token, { method: "POST" }),
  labelPdfUrl: (id: string) => `${B}/${id}/labels.pdf`,
  labelsPdfUrl: (id: string) => `${B}/${id}/labels.pdf`,
  pickupManifestPdfUrl: (ids: string[]) => {
    const p = new URLSearchParams();
    ids.forEach((id) => p.append("ids", id));
    return `${B}/pickup-manifest.pdf?${p.toString()}`;
  },
  manifestPdfUrl: (id: string) => `${B}/${id}/manifest.pdf`,
  compliancePdfUrl: (id: string) => `${B}/${id}/compliance-dossier.pdf`,
  invoicePdfUrl: (id: string) => `${B}/${id}/invoice.pdf`,
  assist: (token: string, id: string) => adminFetch<AssistPayload>(`${B}/${id}/assist`, token),
  assistDecide: (
    token: string,
    id: string,
    body: { proposal_id: string; decision: "accept" | "reject"; payload?: Record<string, unknown> }
  ) =>
    adminFetch<{ ok: boolean; decision: string; result?: unknown }>(
      `${B}/${id}/assist/decide`,
      token,
      {
        method: "POST",
        body: JSON.stringify(body),
      }
    ),
  runPlaybook: (
    token: string,
    id: string,
    playbookId: string,
    body: { confirm: boolean; note?: string }
  ) =>
    adminFetch<{ ok: boolean; playbook_id: string; result?: unknown }>(
      `${B}/${id}/playbooks/${playbookId}`,
      token,
      { method: "POST", body: JSON.stringify(body) }
    ),
  shopifyRelease: (token: string, id: string) =>
    adminFetch<{ ok: boolean; order_id: string; state: string }>(
      `${B}/${id}/shopify/release`,
      token,
      { method: "POST", body: "{}" }
    ),
  shopifyRepushFulfillment: (token: string, id: string) =>
    adminFetch<{
      ok: boolean;
      order_id: string;
      fulfillment_id?: string | null;
      last_tracking_push_at?: string | null;
      last_tracking_state?: string | null;
    }>(`${B}/${id}/shopify/repush-fulfillment`, token, { method: "POST", body: "{}" }),
  amendParcels: (
    token: string,
    id: string,
    payload: { stops: Array<Record<string, unknown>>; vehicle_class?: string }
  ) =>
    adminFetch<{
      order_id: string;
      state: string;
      amount_cents: number;
      quote: Record<string, unknown> | null;
      stops: Array<Record<string, unknown>>;
      parcel_amendable: boolean;
    }>(`${B}/${id}/parcels`, token, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
};

export type AssistProposal = {
  id: string;
  kind: string;
  title: string;
  summary: string;
  confidence: string;
  preview: Record<string, unknown>;
  requires_confirm: boolean;
  payload: Record<string, unknown>;
  draft_source?: "heuristic" | "nvidia_nim" | string;
};

export type Playbook = {
  id: string;
  label: string;
  description: string;
  enabled: boolean;
  disabled_reason?: string | null;
};

export type AssistPayload = {
  order_id: string;
  tracking_number: string;
  state: string;
  contract: Record<string, unknown>;
  proposals: AssistProposal[];
  playbooks: Playbook[];
  generated_at: string;
};

/** The filename the API chose, when it sent one. */
function filenameFromHeader(header: string | null): string | null {
  const match = /filename\*?=(?:UTF-8'')?"?([^";]+)"?/i.exec(header ?? "");
  return match ? decodeURIComponent(match[1]).trim() || null : null;
}

/**
 * Download an authenticated admin file (labels, manifest, POD media).
 *
 * `filename` is the fallback: the API names its own downloads, and for POD the
 * extension is only known server-side once the media type is read.
 */
export async function downloadOrderFile(token: string, path: string, filename: string) {
  const headers: Record<string, string> = {};
  if (token === "dev") {
    headers.Authorization = "Bearer dev";
  } else {
    headers.Authorization = `Bearer ${token}`;
  }
  const res = await fetch(`/api/porterchain${path.startsWith("/") ? path : `/${path}`}`, {
    credentials: "include",
    headers,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    const detail = (body as { detail?: string }).detail;
    throw new Error(typeof detail === "string" ? detail : `Download failed (${res.status})`);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filenameFromHeader(res.headers.get("Content-Disposition")) ?? filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** Every POD photo and the signature for one shipment, zipped (BR). */
export const podBundlePath = (orderId: string) => `/v1/admin/orders/${orderId}/pod.zip`;

/** One POD photo or the signature, by the handle the gallery carries (BR). */
export const podArtifactPath = (orderId: string, slug: string) =>
  `/v1/admin/orders/${orderId}/pod/${encodeURIComponent(slug)}`;

export const STATE_STYLES: Record<string, string> = {
  BOOKED: "bg-blue-100 text-blue-700",
  DISPATCH_READY: "bg-indigo-100 text-indigo-700",
  DRIVER_ASSIGNED: "bg-violet-100 text-violet-700",
  DRIVER_ACCEPTED: "bg-violet-100 text-violet-700",
  DRIVER_EN_ROUTE: "bg-purple-100 text-purple-700",
  AT_PICKUP: "bg-amber-100 text-amber-800",
  PICKED_UP: "bg-teal-100 text-teal-800",
  IN_TRANSIT: "bg-cyan-100 text-cyan-800",
  AT_DESTINATION: "bg-sky-100 text-sky-800",
  DELIVERED: "bg-green-100 text-green-700",
  POD_COMPLETED: "bg-green-100 text-green-700",
  INVOICED: "bg-emerald-100 text-emerald-800",
  CLOSED: "bg-gray-100 text-gray-600",
  CANCELLED: "bg-red-100 text-red-700",
  FAILED: "bg-red-100 text-red-700",
  RETURN_TO_SENDER: "bg-orange-100 text-orange-800",
  DAMAGED: "bg-red-100 text-red-700",
  LOST: "bg-red-100 text-red-700",
  CLAIM_OPEN: "bg-amber-100 text-amber-800",
  REFUNDED: "bg-gray-100 text-gray-500",
};

export const PAYMENT_STYLES: Record<string, string> = {
  SUCCEEDED: "bg-green-100 text-green-700",
  PROCESSING: "bg-amber-100 text-amber-700",
  PENDING: "bg-gray-100 text-gray-600",
  FAILED: "bg-red-100 text-red-700",
};

export const SLA_STYLES: Record<string, string> = {
  met: "bg-green-100 text-green-700",
  ok: "bg-blue-50 text-blue-700",
  at_risk: "bg-amber-100 text-amber-800",
  breached: "bg-red-100 text-red-700",
};

export function exportOrdersCsv(rows: OrderRow[], filename = "orders.csv") {
  const headers = [
    "order_number",
    "tracking_number",
    "booking_number",
    "state",
    "merchant_name",
    "customer_email",
    "driver_name",
    "pickup",
    "destination",
    "payment_status",
    "amount_cents",
    "priority",
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

export function formatState(s: string) {
  return s.replace(/_/g, " ");
}

const ORDER_SOURCE_LABELS: Record<string, string> = {
  WEBSITE: "Website",
  MERCHANT: "Merchant portal",
  API: "API",
  CSV: "CSV",
  ADMIN: "Admin",
  PHONE: "Phone",
  PARTNER: "Partner",
  SHOPIFY: "Shopify",
};

export function orderSourceLabel(source: string | null | undefined): string {
  if (!source) return "—";
  return ORDER_SOURCE_LABELS[source] ?? source.replace(/_/g, " ");
}

export function shopifyAdminUrl(
  shop:
    | {
        shop_domain?: string | null;
        order_id?: string | null;
      }
    | null
    | undefined
): string | null {
  const domain = shop?.shop_domain?.trim();
  const id = shop?.order_id?.trim();
  if (!domain || !id || !domain.includes(".")) return null;
  return `https://${domain}/admin/orders/${encodeURIComponent(id)}`;
}
