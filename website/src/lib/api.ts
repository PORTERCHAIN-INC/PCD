import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl || "http://localhost:8001";

export interface AddressPayload {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
}

export interface VisitorTrackingPayload {
  browser?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  referrer?: string;
  device?: string;
  location?: { city?: string; region?: string; country?: string };
}

export interface PricingLineItem {
  code: string;
  label: string;
  amount_cents: number;
}

export interface WebsitePricingSnapshot {
  customer_price_cad: number;
  driver_payout_cad: number;
  platform_margin_cad: number;
  distance_km: number;
  duration_minutes: number;
  engine_vehicle_id: string;
  breakdown: Record<string, number>;
  traffic?: Record<string, unknown>;
  quote_engine?: string;
}

export interface QuoteResult {
  quote_id: string;
  state: string;
  amount_cents: number;
  amount_display: string;
  expires_at: string;
  distance_km?: number;
  vehicle_class: string;
  scheduled_at: string;
  pricing_breakdown?: PricingLineItem[];
  pickup?: AddressPayload | null;
  dropoff?: AddressPayload | null;
  package_type?: string | null;
  weight_kg?: number | null;
  dimensions?: string | null;
  additional_stops?: AddressPayload[] | null;
  special_instructions?: string | null;
}

export interface CreateQuotePayload {
  anonymous_session_id?: string;
  visitor_session_id?: string;
  pickup: AddressPayload;
  dropoff: AddressPayload;
  vehicle_class: string;
  package_type: string;
  weight_kg?: number;
  dimensions?: string;
  declared_value_cents?: number;
  additional_stops?: AddressPayload[];
  special_instructions?: string;
  scheduled_at: string;
  schedule_mode: "now" | "later";
  tracking?: VisitorTrackingPayload;
  website_pricing?: WebsitePricingSnapshot;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function createQuote(payload: CreateQuotePayload) {
  return apiFetch<QuoteResult>("/v1/quotes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getQuote(quoteId: string) {
  return apiFetch<QuoteResult>(`/v1/quotes/${quoteId}`);
}

export interface StartBookingPayload {
  quote_id: string;
  email: string;
  phone: string;
  clerk_user_id: string;
  anonymous_session_id?: string;
  terms_accepted?: boolean;
  privacy_accepted?: boolean;
  dangerous_goods_confirmed?: boolean;
  consent_at?: string;
}

export interface BookingResult {
  quote_id: string;
  state: string;
  customer_id: string;
  checkout_url: string | null;
  mock_checkout: boolean;
}

export function startBooking(payload: StartBookingPayload, token?: string) {
  return apiFetch<BookingResult>("/v1/bookings", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: JSON.stringify(payload),
  });
}

export interface BookingConfirmationResult {
  booking_id: string;
  booking_number: string;
  order_id: string;
  order_number: string;
  tracking_number: string;
  invoice_id: string;
  invoice_number: string;
  receipt_number?: string | null;
  payment_reference?: string | null;
  customer_reference?: string | null;
  payment_method?: string | null;
  receipt_url?: string | null;
  tax_cents?: number;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: { formatted?: string };
  dropoff: { formatted?: string };
  fleetbase_order_id?: string | null;
  dashboard_url: string;
}

export interface BookingConfirmationStatus {
  status: "processing" | "ready";
  confirmation: BookingConfirmationResult | null;
}

export function getBookingConfirmation(quoteId: string) {
  return apiFetch<BookingConfirmationStatus>(
    `/v1/bookings/confirmation?quote_id=${encodeURIComponent(quoteId)}`
  );
}

export interface OrderResult {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: { formatted?: string };
  dropoff: { formatted?: string };
  booking_number?: string | null;
  invoice_number?: string | null;
}

export function mockCompleteCheckout(quoteId: string) {
  return apiFetch<BookingConfirmationResult>("/v1/bookings/mock-complete", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export function getOrderByTracking(trackingNumber: string) {
  return apiFetch<OrderResult>(`/v1/orders/${trackingNumber}`);
}

export interface CustomerDashboard {
  active_order: OrderResult | null;
  orders: OrderResult[];
  bookings: Array<{
    booking_id: string;
    booking_number: string;
    state: string;
    quote_id: string;
    order_id: string | null;
    created_at: string;
  }>;
  invoices: Array<{
    invoice_id: string;
    invoice_number: string;
    order_id: string;
    amount_cents: number;
    currency: string;
    stripe_receipt_url: string | null;
    pdf_url: string | null;
    created_at: string;
  }>;
  payments: Array<{
    payment_id: string;
    status: string;
    amount_cents: number;
    currency: string;
    failure_reason: string | null;
    receipt_url: string | null;
    retry_count: number;
    quote_id: string;
    order_id: string | null;
  }>;
  stats: { total_orders: number; total_bookings: number };
}

export function getCustomerDashboard(token: string) {
  return apiFetch<CustomerDashboard>("/v1/customers/me/dashboard", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function createCustomerSupportTicket(
  token: string,
  payload: { subject: string; description?: string; order_id?: string }
) {
  return apiFetch<{ ticket_id: string; status: string; subject: string }>("/v1/customers/me/support", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });
}

export function getCustomerRebookPayload(token: string, orderId: string) {
  return apiFetch<{
    pickup: AddressPayload;
    dropoff: AddressPayload;
    vehicle_class: string | null;
    source_order_id: string;
    tracking_number: string;
  }>(`/v1/customers/me/rebook/${orderId}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function retryPayment(quoteId: string, token: string) {
  return apiFetch<{ payment_id: string; checkout_url: string | null; status: string }>(
    "/v1/payments/retry",
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ quote_id: quoteId }),
    }
  );
}

export interface BookingDraftResult {
  draft_id: string;
  session_id: string;
  customer_id: string | null;
  quote_id: string | null;
  state: string;
  current_step: string;
  payment_status: string | null;
  pickup?: AddressPayload | null;
  dropoff?: AddressPayload | null;
  vehicle_class?: string | null;
  package_type?: string | null;
  amount_cents?: number | null;
  expires_at: string;
  continue_url?: string | null;
}

export function createBookingDraft(payload: {
  session_id: string;
  pickup?: AddressPayload;
  dropoff?: AddressPayload;
  vehicle_class?: string;
  package_type?: string;
  weight_kg?: number;
  dimensions?: string;
  current_step?: string;
}) {
  return apiFetch<BookingDraftResult>("/v1/booking-drafts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getActiveBookingDraft(
  sessionId: string,
  token?: string
): Promise<BookingDraftResult | null> {
  const params = new URLSearchParams({ session_id: sessionId });
  const response = await fetch(`${API_BASE}/v1/booking-drafts/active?${params}`, {
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  const data = (await response.json()) as BookingDraftResult | null;
  return data ?? null;
}
