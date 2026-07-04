import { z } from "zod";
import { adminFetch } from "@/lib/api";

const draftItemSchema = z.object({
  draft_id: z.string(),
  draft_number: z.string(),
  session_id: z.string(),
  visitor_id: z.string().nullable().optional(),
  customer_id: z.string().nullable(),
  customer_email: z.string().nullable(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  quote_id: z.string().nullable(),
  booking_type: z.string(),
  state: z.string(),
  display_state: z.string(),
  current_step: z.string(),
  payment_status: z.string().nullable(),
  vehicle_class: z.string().nullable().optional(),
  amount_cents: z.number().nullable(),
  currency: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  expires_at: z.string(),
  is_expired: z.boolean(),
  is_abandoned: z.boolean(),
  booking_id: z.string().nullable().optional(),
  order_id: z.string().nullable().optional(),
});

export type BookingDraftRow = z.infer<typeof draftItemSchema>;

export const draftDetailSchema = draftItemSchema.extend({
  pickup: z.record(z.string(), z.unknown()).nullable().optional(),
  dropoff: z.record(z.string(), z.unknown()).nullable().optional(),
  additional_stops: z.array(z.record(z.string(), z.unknown())).nullable().optional(),
  package_type: z.string().nullable().optional(),
  weight_kg: z.number().nullable().optional(),
  dimensions: z.string().nullable().optional(),
  declared_value_cents: z.number().nullable().optional(),
  special_instructions: z.string().nullable().optional(),
  pricing_breakdown: z.record(z.string(), z.unknown()).nullable().optional(),
  taxes_cents: z.number().optional(),
  discounts_cents: z.number().optional(),
  promo_code: z.string().nullable().optional(),
  distance_meters: z.number().nullable().optional(),
  estimated_pickup: z.string().nullable().optional(),
  estimated_delivery: z.string().nullable().optional(),
  schedule_mode: z.string().nullable().optional(),
  stripe_checkout_session_id: z.string().nullable().optional(),
  stripe_payment_intent_id: z.string().nullable().optional(),
  payment_id: z.string().nullable().optional(),
  quote_amount_cents: z.number().nullable().optional(),
  quote_state: z.string().nullable().optional(),
  continue_url: z.string().nullable().optional(),
  abandoned_minutes: z.number().nullable().optional(),
  audits: z.array(z.record(z.string(), z.unknown())),
  domain_events: z.array(z.record(z.string(), z.unknown())),
});

export type BookingDraftDetail = z.infer<typeof draftDetailSchema>;

export type BookingDraftAnalytics = {
  total_drafts: number;
  confirmed_drafts: number;
  conversion_rate_percent: number;
  abandonment_rate_percent: number;
  payment_success_rate_percent: number;
  avg_completion_minutes: number;
  most_common_failure_step: string | null;
  revenue_lost_cents: number;
  recovery_rate_percent: number;
  active_drafts: number;
  abandoned_now: number;
};

export type DraftFilters = {
  state?: string;
  search?: string;
  booking_type?: string;
  vehicle_class?: string;
  payment_status?: string;
  current_step?: string;
  date_from?: string;
  date_to?: string;
  price_min_cents?: number;
  price_max_cents?: number;
  expired_only?: boolean;
  abandoned_only?: boolean;
};

const B = "/v1/admin/booking-drafts";

function qs(filters?: DraftFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "" && v !== false) p.set(k, String(v));
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const bookingDraftsApi = {
  list: async (token: string, filters?: DraftFilters) => {
    const raw = await adminFetch<unknown[]>(`${B}${qs(filters)}`, token);
    return z.array(draftItemSchema).parse(raw);
  },
  analytics: (token: string) => adminFetch<BookingDraftAnalytics>(`${B}/analytics`, token),
  abandoned: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/abandoned`, token);
    return z.array(draftItemSchema.extend({ abandoned_minutes: z.number(), last_step: z.string(), reason: z.string() })).parse(raw);
  },
  detail: async (token: string, draftId: string) => {
    const raw = await adminFetch<unknown>(`${B}/${draftId}`, token);
    return draftDetailSchema.parse(raw);
  },
  extend: (token: string, draftId: string, extraMinutes?: number) =>
    adminFetch<BookingDraftDetail>(`${B}/${draftId}/extend`, token, {
      method: "POST",
      body: JSON.stringify({ extra_minutes: extraMinutes }),
    }),
  cancel: (token: string, draftId: string, reason?: string) =>
    adminFetch<BookingDraftDetail>(`${B}/${draftId}/cancel`, token, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  restore: (token: string, draftId: string) =>
    adminFetch<BookingDraftDetail>(`${B}/${draftId}/restore`, token, { method: "POST" }),
  expire: (token: string, draftId: string) =>
    adminFetch<BookingDraftDetail>(`${B}/${draftId}/expire`, token, { method: "POST" }),
  duplicate: (token: string, draftId: string) =>
    adminFetch<BookingDraftDetail>(`${B}/${draftId}/duplicate`, token, { method: "POST" }),
  sendPaymentLink: (token: string, draftId: string) =>
    adminFetch<{ checkout_url: string | null; payment_id: string | null }>(
      `${B}/${draftId}/send-payment-link`,
      token,
      { method: "POST" }
    ),
  bulk: (token: string, draftIds: string[], action: string, opts?: { extra_minutes?: number; reason?: string }) =>
    adminFetch<{ action: string; results: Array<{ draft_id: string; status: string }> }>(`${B}/bulk`, token, {
      method: "POST",
      body: JSON.stringify({ draft_ids: draftIds, action, ...opts }),
    }),
};

export const DRAFT_STATES = [
  "DRAFT",
  "QUOTE_GENERATED",
  "CUSTOMER_IDENTIFIED",
  "AUTHENTICATED",
  "PAYMENT_PENDING",
  "PAYMENT_FAILED",
  "PAYMENT_COMPLETED",
  "BOOKING_CONFIRMED",
  "CONVERTED_TO_ORDER",
  "EXPIRED",
  "CANCELLED",
] as const;

export const STATE_STYLES: Record<string, string> = {
  DRAFT: "bg-gray-100 text-gray-600",
  QUOTE_GENERATED: "bg-blue-100 text-blue-700",
  CUSTOMER_IDENTIFIED: "bg-indigo-100 text-indigo-700",
  AUTHENTICATED: "bg-violet-100 text-violet-700",
  PAYMENT_PENDING: "bg-amber-100 text-amber-700",
  PAYMENT_FAILED: "bg-red-100 text-red-700",
  PAYMENT_COMPLETED: "bg-green-100 text-green-700",
  BOOKING_CONFIRMED: "bg-green-100 text-green-800",
  CONVERTED_TO_ORDER: "bg-teal-100 text-teal-800",
  EXPIRED: "bg-orange-100 text-orange-700",
  CANCELLED: "bg-gray-100 text-gray-500",
};

export const PAYMENT_STATUS_STYLES: Record<string, string> = {
  SUCCEEDED: "bg-green-100 text-green-700",
  PROCESSING: "bg-amber-100 text-amber-700",
  PENDING: "bg-gray-100 text-gray-600",
  FAILED: "bg-red-100 text-red-700",
};

export function exportCsv(rows: BookingDraftRow[], filename = "booking-drafts.csv") {
  const headers = [
    "draft_number",
    "display_state",
    "customer_email",
    "merchant_name",
    "booking_type",
    "vehicle_class",
    "amount_cents",
    "payment_status",
    "current_step",
    "created_at",
    "updated_at",
    "expires_at",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => {
          const v = r[h as keyof BookingDraftRow];
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
