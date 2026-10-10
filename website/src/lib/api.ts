import type {
  DeliveryInstructions,
  DeliveryManageOptions,
  TrackingExperience,
} from "@porterchain/types";
import { getPorterchainApiBase } from "@/lib/api-base";

const API_BASE = getPorterchainApiBase();

export interface AddressPayload {
  formatted?: string;
  city?: string;
  province?: string;
  postal_code?: string;
  country?: string;
  place_id?: string;
  lat?: number;
  lng?: number;
}

export interface OrderResult {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: AddressPayload;
  dropoff: AddressPayload;
  booking_number?: string | null;
  invoice_number?: string | null;
  company_name?: string | null;
  logo_url?: string | null;
  tracking_page_message?: string | null;
}

export interface TrackingEta {
  source?: string;
  duration_seconds?: number;
  distance_meters?: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
}

export interface OrderLiveTracking {
  order_id: string;
  tracking_number: string;
  state: string;
  fleetbase_order_id?: string | null;
  live_tracking?: {
    pickup?: AddressPayload;
    dropoff?: AddressPayload;
    driver_location?: { lat: number; lng: number; source?: string; recorded_at?: string };
    optimized_route?: { polyline?: string; source?: string };
    eta?: TrackingEta | null;
    delivery_status?: {
      order_state?: string;
      label?: string;
      in_transit?: boolean;
      delivered?: boolean;
    };
    last_updated?: string;
    branding?: {
      company_name?: string | null;
      logo_url?: string | null;
      tracking_page_message?: string | null;
    } | null;
  } | null;
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

/** Public guest tracking (no account). */
export function getOrderByTracking(trackingNumber: string) {
  return apiFetch<OrderResult>(`/v1/orders/${trackingNumber}`, { cache: "no-store" });
}

export function getOrderLiveTracking(trackingNumber: string) {
  return apiFetch<OrderLiveTracking>(`/v1/orders/${trackingNumber}/tracking`, {
    cache: "no-store",
  });
}

/** Branded recipient view (enhanced: false unless the merchant turned it on). */
export function getOrderExperience(trackingNumber: string, manageToken?: string | null) {
  return apiFetch<TrackingExperience>(
    `/v1/orders/${encodeURIComponent(trackingNumber)}/experience`,
    {
      cache: "no-store",
      headers: manageToken ? { "X-Manage-Token": manageToken } : undefined,
    }
  );
}

export interface ManageApiError extends Error {
  code: string | null;
  status: number;
}

async function manageFetch<T>(path: string, token: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    cache: "no-store",
    referrerPolicy: "no-referrer",
    headers: {
      "Content-Type": "application/json",
      "X-Manage-Token": token,
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { code?: string; message?: string } | string;
    };
    const detail = body.detail;
    const err = new Error(
      typeof detail === "string" ? detail : detail?.message || `API error ${response.status}`
    ) as ManageApiError;
    err.code = typeof detail === "object" && detail ? (detail.code ?? null) : null;
    err.status = response.status;
    throw err;
  }
  return response.json() as Promise<T>;
}

export function getDeliveryManageOptions(trackingNumber: string, token: string) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}`,
    token
  );
}

export function postDeliverySchedule(trackingNumber: string, token: string, windowCode: string) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}/schedule`,
    token,
    { method: "POST", body: JSON.stringify({ window_code: windowCode }) }
  );
}

export function postDeliveryInstructions(
  trackingNumber: string,
  token: string,
  instructions: DeliveryInstructions
) {
  return manageFetch<DeliveryManageOptions>(
    `/v1/delivery-manage/${encodeURIComponent(trackingNumber)}/instructions`,
    token,
    { method: "POST", body: JSON.stringify(instructions) }
  );
}

// ---------------------------------------------------------------------------
// Fast book (guest checkout), tracking actions, Send again, email preferences.

export interface FastApiError extends Error {
  code: string | null;
  status: number;
}

async function fastFetch<T>(path: string, init?: RequestInit & { token?: string }): Promise<T> {
  const { token, ...rest } = init ?? {};
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    cache: "no-store",
    referrerPolicy: "no-referrer",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Manage-Token": token } : {}),
      ...rest.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: { code?: string; message?: string } | string | Array<unknown>;
    };
    const detail = body.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail && !Array.isArray(detail) && detail.message
          ? detail.message
          : "Something went wrong. Try again.";
    const err = new Error(message) as FastApiError;
    err.code =
      detail && typeof detail === "object" && !Array.isArray(detail) ? (detail.code ?? null) : null;
    err.status = response.status;
    throw err;
  }
  return response.json() as Promise<T>;
}

export interface FastAddress {
  formatted: string;
  postal?: string;
}

export interface FastQuoteInput {
  pickup: FastAddress;
  dropoff: FastAddress;
  additional_stops?: FastAddress[];
  vehicle_class: string;
  scheduled_at: string;
  anonymous_session_id?: string;
}

export interface FastPreview {
  amount_cents: number;
  amount_display: string;
  pricing_breakdown: Array<{ code: string; label: string; amount_cents: number }>;
}

export interface FastQuote extends FastPreview {
  quote_id: string;
  pickup?: { formatted?: string } | null;
  dropoff?: { formatted?: string } | null;
  additional_stops?: { formatted?: string }[] | null;
  vehicle_class: string;
}

function quoteBody(input: FastQuoteInput) {
  return JSON.stringify({ ...input, booking_mode: "vehicle", schedule_mode: "now" });
}

export function fastPreview(input: FastQuoteInput) {
  return fastFetch<FastPreview>("/v1/quotes/preview", { method: "POST", body: quoteBody(input) });
}

export function fastCreateQuote(input: FastQuoteInput) {
  return fastFetch<FastQuote>("/v1/quotes", { method: "POST", body: quoteBody(input) });
}

export function fastGetQuote(quoteId: string) {
  return fastFetch<FastQuote>(`/v1/quotes/${encodeURIComponent(quoteId)}`);
}

export interface ExpressCheckoutInput {
  quote_id: string;
  name: string;
  email: string;
  phone: string;
  terms_accepted: boolean;
  privacy_accepted: boolean;
  dangerous_goods_confirmed: boolean;
  marketing_opt_in: boolean;
  anonymous_session_id?: string;
  website: string;
  form_elapsed_ms: number;
  locale?: "en" | "fr";
}

export function expressCheckout(input: ExpressCheckoutInput) {
  return fastFetch<{ quote_id: string; checkout_url: string | null; mock_checkout: boolean }>(
    "/v1/express/checkout",
    { method: "POST", body: JSON.stringify(input) }
  );
}

/** Local/dev only (server refuses in production): completes a mock Stripe payment. */
export function mockCompleteCheckout(quoteId: string) {
  return fastFetch<unknown>("/v1/bookings/mock-complete", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export interface ExpressConfirmation {
  status: "processing" | "ready";
  tracking_number?: string;
  order_number?: string;
  amount_cents?: number;
  receipt_url?: string | null;
  receipt_number?: string | null;
  manage_track_url?: string;
}

export function expressConfirmation(quoteId: string) {
  return fastFetch<ExpressConfirmation>(
    `/v1/express/confirmation?quote_id=${encodeURIComponent(quoteId)}`
  );
}

export function syncCheckout(quoteId: string) {
  return fastFetch<unknown>("/v1/bookings/sync-checkout", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export interface SendAgainResult {
  quote: FastQuote;
  contact: { email: string; phone: string; name: string };
  source_tracking_number: string;
}

export function sendAgain(token: string) {
  return fastFetch<SendAgainResult>("/v1/express/send-again", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export interface OrderActions {
  tracking_number: string;
  state: string;
  retail: boolean;
  can_cancel: boolean;
  cancel_rule: string;
  refund: { status: string; amount_cents?: number } | null;
  receipt: {
    receipt_number?: string | null;
    invoice_number?: string | null;
    amount_cents?: number;
    url?: string | null;
  } | null;
  can_rate: boolean;
  rating: { score: number } | null;
  send_again_url: string | null;
}

export function getOrderActions(tracking: string, token: string) {
  return fastFetch<OrderActions>(`/v1/delivery-manage/${encodeURIComponent(tracking)}/actions`, {
    token,
  });
}

export function cancelOrder(tracking: string, token: string) {
  return fastFetch<OrderActions>(`/v1/delivery-manage/${encodeURIComponent(tracking)}/cancel`, {
    method: "POST",
    token,
  });
}

export function rateOrder(tracking: string, token: string, score: number, comment: string) {
  return fastFetch<OrderActions>(`/v1/delivery-manage/${encodeURIComponent(tracking)}/rating`, {
    method: "POST",
    token,
    body: JSON.stringify({ score, comment: comment || null }),
  });
}

export interface EmailPreferences {
  email: string;
  preferences: { tracking: boolean; reorder: boolean; marketing: boolean };
  marketing_consent_at: string | null;
  deletion_requested: boolean;
  portal_url: string;
}

export function readEmailPreferences(token: string) {
  return fastFetch<EmailPreferences>("/v1/email-preferences/read", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function saveEmailPreferences(
  token: string,
  prefs: Partial<EmailPreferences["preferences"]>
) {
  return fastFetch<EmailPreferences>("/v1/email-preferences", {
    method: "POST",
    body: JSON.stringify({ token, ...prefs }),
  });
}

export function unsubscribeAll(token: string) {
  return fastFetch<EmailPreferences>("/v1/email-preferences/unsubscribe", {
    method: "POST",
    body: JSON.stringify({ token }),
  });
}

export function requestDataDeletion(token: string) {
  return fastFetch<{ reference: string; status: string; sla_days: number }>(
    "/v1/email-preferences/delete-request",
    { method: "POST", body: JSON.stringify({ token }) }
  );
}

export type ProblemKind =
  "late" | "damaged" | "missing" | "wrong_address" | "return" | "billing" | "other";

/** Report a problem / request a return from the signed tracking page (opens a ticket). */
export function reportProblem(tracking: string, token: string, kind: ProblemKind, details: string) {
  return fastFetch<{ status: string; ticket_id: string | null; reply_within_hours: number }>(
    `/v1/delivery-manage/${encodeURIComponent(tracking)}/problem`,
    { method: "POST", body: JSON.stringify({ token, kind, details: details || null }) }
  );
}
