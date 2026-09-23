import * as Crypto from "expo-crypto";
import { apiBaseUrl, fetchTimeoutMs } from "./config";
import { requireBearer } from "./session";

const PORTAL = "customer";

export type Address = {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
  postal?: string;
};

export type OrderResult = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents?: number;
  currency?: string;
  pickup?: Address;
  dropoff?: Address;
  tracking_page_message?: string | null;
};

export type OrderLiveTracking = {
  order_id: string;
  tracking_number: string;
  state: string;
  live_tracking?: {
    delivery_status?: {
      order_state?: string;
      label?: string;
      in_transit?: boolean;
      delivered?: boolean;
    };
    eta?: { label?: string; arrives_at?: string } | null;
  } | null;
};

export type OnboardingStep = {
  id: string;
  label: string;
  description: string;
  complete: boolean;
  status: string;
};

export type OnboardingStatus = {
  ready: boolean;
  blockers: string[];
  status: string;
  steps: OnboardingStep[];
  can_access_portal: boolean;
};

export type SessionContext = {
  email: string | null;
  permissions: string[];
  status: string;
};

export type CustomerOrder = {
  order_id: string;
  order_number?: string;
  tracking_number: string;
  state: string;
  amount_cents?: number;
  currency?: string;
  scheduled_at?: string;
  pickup?: Address | null;
  dropoff?: Address | null;
  created_at?: string;
  goods_summary?: string | null;
  vehicle_class?: string | null;
};

export type CustomerBooking = {
  booking_id: string;
  booking_number?: string;
  state: string;
  quote_id?: string | null;
  order_id?: string | null;
  created_at?: string;
};

export type CustomerInvoice = {
  invoice_id: string;
  invoice_number: string;
  order_id?: string | null;
  amount_cents: number;
  currency: string;
  stripe_receipt_url?: string | null;
  pdf_url?: string | null;
  created_at?: string;
};

export type CustomerPayment = {
  payment_id: string;
  status: string;
  amount_cents: number;
  currency: string;
  failure_reason?: string | null;
  receipt_url?: string | null;
  quote_id?: string | null;
  order_id?: string | null;
};

export type CustomerDashboard = {
  active_order: CustomerOrder | null;
  orders: CustomerOrder[];
  bookings: CustomerBooking[];
  invoices: CustomerInvoice[];
  payments: CustomerPayment[];
  stats: { total_orders?: number; total_bookings?: number };
};

export type SupportTicket = {
  ticket_id: string;
  status: string;
  subject: string;
  description?: string | null;
  order_id?: string | null;
  created_at: string;
};

export type RebookPayload = {
  pickup: Address;
  dropoff: Address;
  vehicle_class: string | null;
  booking_mode?: "parcels" | "vehicle" | null;
  parcels?: Array<{
    preset_id?: string;
    instructions?: string | null;
    length_cm?: number;
    width_cm?: number;
    height_cm?: number;
    weight_kg?: number;
  }> | null;
  declared_value_cents?: number | null;
  source_order_id: string;
  tracking_number: string;
};

export type QuoteLine = { code: string; label: string; amount_cents: number };

export type QuoteResult = {
  quote_id: string;
  state: string;
  amount_cents: number;
  amount_display: string;
  expires_at: string;
  currency?: string;
  distance_km?: number | null;
  pricing_breakdown: QuoteLine[];
  vehicle_class: string;
  package_type?: string | null;
  weight_kg?: number | null;
  dimensions?: string | null;
  booking_mode?: string | null;
  parcels?: Array<{ preset_label?: string; instructions?: string | null }> | null;
  declared_value_cents?: number | null;
};

export type BookingStart = {
  quote_id: string;
  state: string;
  customer_id: string;
  checkout_url: string | null;
  mock_checkout: boolean;
};

export type BookingConfirmation = {
  tracking_number: string;
  order_number: string;
  invoice_number?: string;
  amount_cents: number;
  currency: string;
  state: string;
  vehicle_class?: string | null;
  booking_mode?: string | null;
  parcels?: Array<{ preset_label?: string }> | null;
};

export type QuoteInput = {
  pickup: Address;
  dropoff: Address;
  vehicle_class: string;
  package_type?: string;
  booking_mode?: "parcels" | "vehicle";
  parcels?: Array<{
    preset_id: string;
    quantity: number;
    instructions?: string;
    length_in?: number;
    width_in?: number;
    height_in?: number;
    weight_lb?: number;
  }>;
  weight_kg?: number;
  dimensions?: string;
  declared_value_cents?: number;
  additional_stops?: Address[];
  special_instructions?: string;
  promo_code?: string;
  scheduled_at: string;
  schedule_mode: "now" | "later";
  anonymous_session_id?: string;
  visitor_session_id?: string;
  tracking?: {
    device?: string;
    utm_source?: string;
    utm_medium?: string;
    utm_campaign?: string;
    utm_term?: string;
    utm_content?: string;
    from_page?: string;
    intent?: string;
  };
};

async function fetchWithTimeout(url: string, init: RequestInit = {}): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), fetchTimeoutMs);
  try {
    return await fetch(url, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function readError(res: Response): Promise<string> {
  const text = await res.text();
  if (!text) return `http_${res.status}`;
  try {
    const body = JSON.parse(text) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
  } catch {
    /* plain text */
  }
  return `http_${res.status}`;
}

async function request<T>(path: string, init: RequestInit = {}, auth = false): Promise<T> {
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...(init.headers as Record<string, string> | undefined),
  };
  if (auth) {
    headers.Authorization = `Bearer ${await requireBearer()}`;
    headers["X-Porterchain-Portal"] = PORTAL;
  }
  const res = await fetchWithTimeout(`${apiBaseUrl}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(await readError(res));
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export function formatCad(cents: number, currency = "CAD"): string {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export async function probeApi(): Promise<boolean> {
  try {
    const res = await fetchWithTimeout(`${apiBaseUrl}/health`, { method: "GET" });
    return res.ok;
  } catch {
    return false;
  }
}

export function getOrderByTracking(trackingNumber: string): Promise<OrderResult> {
  return request(`/v1/orders/${encodeURIComponent(trackingNumber)}`);
}

export function getOrderLiveTracking(trackingNumber: string): Promise<OrderLiveTracking> {
  return request(`/v1/orders/${encodeURIComponent(trackingNumber)}/tracking`);
}

export function fetchOnboarding(): Promise<OnboardingStatus> {
  return request("/v1/auth/customer/onboarding", {}, true);
}

export function fetchSessionContext(): Promise<SessionContext> {
  return request("/v1/auth/session-context", {}, true);
}

/** `system:all` does not open the customer app. */
export function hasCustomerAccess(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("customer_portal.access"));
}

export function fetchDashboard(): Promise<CustomerDashboard> {
  return request("/v1/customers/me/dashboard", {}, true);
}

export function listSupport(): Promise<SupportTicket[]> {
  return request("/v1/customers/me/support", {}, true);
}

export function createSupport(body: {
  subject: string;
  description?: string;
  order_id?: string;
}): Promise<SupportTicket> {
  return request(
    "/v1/customers/me/support",
    {
      method: "POST",
      headers: { "Idempotency-Key": Crypto.randomUUID() },
      body: JSON.stringify(body),
    },
    true
  );
}

export function rebook(orderId: string): Promise<RebookPayload> {
  return request(
    `/v1/customers/me/rebook/${encodeURIComponent(orderId)}`,
    { method: "POST" },
    true
  );
}

export function privacyExport(): Promise<Record<string, unknown>> {
  return request("/v1/customers/me/privacy/export", {}, true);
}

export function privacyDeleteRequest(): Promise<{
  reference: string;
  status: string;
  message: string;
}> {
  return request("/v1/customers/me/privacy/delete-request", { method: "POST" }, true);
}

export type QuotePreview = {
  amount_cents: number;
  amount_display: string;
  distance_km?: number | null;
  included_km?: number | null;
};

export type BookingCatalog = {
  vehicles: Array<{
    id: string;
    label: string;
    included_km?: number | null;
    allowed_presets?: string[] | null;
    whole_vehicle_enabled?: boolean;
    capacity_kg?: number | null;
    max_length_cm?: number | null;
    max_width_cm?: number | null;
    max_height_cm?: number | null;
  }>;
  presets: Array<{
    id: string;
    label: string;
    manual?: boolean;
    length_in?: number | null;
    width_in?: number | null;
    height_in?: number | null;
    weight_lb?: number | null;
  }>;
  included_km?: number | null;
};

export function bookingCatalog(): Promise<BookingCatalog> {
  return request("/v1/booking-catalog");
}

export function previewQuote(body: QuoteInput): Promise<QuotePreview> {
  return request("/v1/quotes/preview", { method: "POST", body: JSON.stringify(body) });
}

export function createQuote(body: QuoteInput): Promise<QuoteResult> {
  return request("/v1/quotes", { method: "POST", body: JSON.stringify(body) });
}

export function getQuote(quoteId: string): Promise<QuoteResult> {
  return request(`/v1/quotes/${encodeURIComponent(quoteId)}`);
}

export function startBooking(body: {
  quote_id: string;
  email: string;
  phone: string;
  clerk_user_id: string;
  terms_accepted: boolean;
  privacy_accepted: boolean;
  dangerous_goods_confirmed: boolean;
  consent_at: string;
  anonymous_session_id?: string;
}): Promise<BookingStart> {
  return request(
    "/v1/bookings",
    {
      method: "POST",
      body: JSON.stringify({ checkout_channel: "customer", ...body }),
    },
    true
  );
}

export function mockComplete(quoteId: string): Promise<BookingConfirmation> {
  return request("/v1/bookings/mock-complete", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export function syncCheckout(quoteId: string): Promise<{
  status: "pending" | "processing" | "ready" | "failed";
  confirmation?: BookingConfirmation;
}> {
  return request("/v1/bookings/sync-checkout", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export async function pollCheckout(quoteId: string): Promise<BookingConfirmation> {
  for (let attempt = 0; attempt < 20; attempt += 1) {
    const res = await syncCheckout(quoteId);
    if (res.status === "ready" && res.confirmation) return res.confirmation;
    if (res.status === "failed") throw new Error("payment_failed");
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error("payment_still_processing");
}

export function retryPayment(
  quoteId: string
): Promise<{ checkout_url: string | null; status: string }> {
  return request(
    "/v1/payments/retry",
    {
      method: "POST",
      body: JSON.stringify({ quote_id: quoteId }),
    },
    true
  );
}

export type InboxItem = {
  id: string;
  title: string;
  body: string;
  deep_link?: string | null;
  is_read: boolean;
  created_at: string;
};

export function fetchInbox(): Promise<{ unread_count: number; items: InboxItem[] }> {
  return request("/v1/notifications/inbox?limit=100", {}, true);
}

export function markRead(id: string): Promise<{ ok: boolean }> {
  return request(
    `/v1/notifications/inbox/${encodeURIComponent(id)}/read`,
    { method: "POST" },
    true
  );
}

export function markAllRead(): Promise<{ ok: boolean }> {
  return request("/v1/notifications/inbox/mark-all-read", { method: "POST" }, true);
}
