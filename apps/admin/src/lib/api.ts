import { publicEnv, isLocalDev } from "@/lib/env";
import { STAFF_COOKIE_TOKEN } from "@/lib/staff-session";

/** Same-origin BFF attaches Staff IdP Bearer from HttpOnly cookie. */
const BFF_PREFIX = "/api/porterchain";

export async function adminFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & {
    role?: string;
    timeoutMs?: number;
    /** Skip BFF (rare). */ direct?: boolean;
  }
): Promise<T> {
  const useBff = !init?.direct;
  const url = useBff
    ? `${BFF_PREFIX}${path.startsWith("/") ? path : `/${path}`}`
    : `${publicEnv.porterchainApiUrl}${path.startsWith("/") ? path : `/${path}`}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.role && isLocalDev() ? { "X-Admin-Role": init.role } : {}),
  };
  if (token === "dev") {
    headers.Authorization = "Bearer dev";
  } else if (!useBff && token.startsWith("staff_sess_")) {
    headers.Authorization = `Bearer ${token}`;
  } else if (token && token !== STAFF_COOKIE_TOKEN) {
    // Legacy callers may still pass a real bearer; BFF ignores non-dev and uses cookie.
    headers.Authorization = `Bearer ${token}`;
  } else {
    headers.Authorization = `Bearer ${STAFF_COOKIE_TOKEN}`;
  }

  const timeoutMs = init?.timeoutMs ?? 15_000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, {
      ...init,
      credentials: "include",
      signal: controller.signal,
      headers: { ...headers, ...(init?.headers as Record<string, string>) },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      const detail = body.detail;
      let message: string;
      if (typeof detail === "string") {
        message = detail;
      } else if (Array.isArray(detail)) {
        message = detail
          .map((d: { msg?: string }) => d.msg)
          .filter(Boolean)
          .join(", ");
      } else if (detail && typeof detail === "object") {
        const d = detail as { code?: string; current_version?: number; expected_version?: number };
        if (d.code === "sequence_version_conflict") {
          message =
            "Sequence conflict — another optimize won the race. Refresh and re-run preview.";
        } else {
          message = d.code || `API ${res.status}`;
        }
      } else {
        message = `API ${res.status}`;
      }
      throw new Error(message || `API ${res.status}`);
    }
    if (res.status === 204) return undefined as T;
    return res.json();
  } catch (err) {
    if (err instanceof Error && err.name === "AbortError") {
      throw new Error("porterchain_api_timeout");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export type AdminDashboard = {
  todays_revenue_cents: number;
  todays_bookings: number;
  pending_quotes: number;
  pending_merchant_approvals: number;
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

export type BookingDraftItem = {
  draft_id: string;
  session_id: string;
  customer_id: string | null;
  customer_email: string | null;
  quote_id: string | null;
  state: string;
  current_step: string;
  payment_status: string | null;
  amount_cents: number | null;
  created_at: string;
  updated_at: string;
  expires_at: string;
};

export type BookingDraftDetail = BookingDraftItem & {
  pickup: Record<string, unknown> | null;
  dropoff: Record<string, unknown> | null;
  vehicle_class: string | null;
  package_type: string | null;
  booking_id: string | null;
  order_id: string | null;
  continue_url: string | null;
  audits: Array<{
    event_label: string;
    from_state: string | null;
    to_state: string;
    actor_type: string;
    actor_id: string | null;
    occurred_at: string;
    payload: Record<string, unknown>;
  }>;
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
  assignDriver: (t: string, orderId: string, driverId: string) =>
    adminFetch<Record<string, unknown>>(`/v1/admin/dispatch/orders/${orderId}/assign`, t, {
      method: "POST",
      body: JSON.stringify({ driver_id: driverId }),
    }),
  orders: (t: string, params?: { state?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set("state", params.state);
    if (params?.search) qs.set("search", params.search);
    const q = qs.toString();
    return adminFetch<{ items: Array<Record<string, unknown>> }>(
      `/v1/admin/orders${q ? `?${q}` : ""}`,
      t
    ).then((page) => page.items);
  },
  orderDetail: (t: string, orderId: string) =>
    adminFetch<OrderDetail>(`/v1/admin/orders/${orderId}`, t),
  orderTimeline: (t: string, orderId: string) =>
    adminFetch<Array<Record<string, unknown>>>(`/v1/admin/orders/${orderId}/timeline`, t),
  bookingDrafts: (t: string, params?: { state?: string; search?: string }) => {
    const qs = new URLSearchParams();
    if (params?.state) qs.set("state", params.state);
    if (params?.search) qs.set("search", params.search);
    const q = qs.toString();
    return adminFetch<BookingDraftItem[]>(`/v1/admin/booking-drafts${q ? `?${q}` : ""}`, t);
  },
  bookingDraftDetail: (t: string, draftId: string) =>
    adminFetch<BookingDraftDetail>(`/v1/admin/booking-drafts/${draftId}`, t),
  extendBookingDraft: (t: string, draftId: string, extraMinutes?: number) =>
    adminFetch<BookingDraftDetail>(`/v1/admin/booking-drafts/${draftId}/extend`, t, {
      method: "POST",
      body: JSON.stringify({ extra_minutes: extraMinutes }),
    }),
  cancelBookingDraft: (t: string, draftId: string, reason?: string) =>
    adminFetch<BookingDraftDetail>(`/v1/admin/booking-drafts/${draftId}/cancel`, t, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  claims: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/claims", t),
  financeSummary: (t: string) => adminFetch<Record<string, number>>("/v1/admin/finance/summary", t),
  tickets: (t: string) =>
    adminFetch<Array<Record<string, unknown>>>("/v1/admin/support/tickets", t),
  reports: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/reports/summary", t),
  staff: (t: string) => adminFetch<Array<Record<string, unknown>>>("/v1/admin/settings/staff", t),
  systemConfig: (t: string) => adminFetch<Record<string, unknown>>("/v1/admin/settings/config", t),
};
