import { publicEnv } from "./env";

export type AddressPayload = {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
};

export type QuoteResult = {
  quote_id: string;
  state: string;
  amount_cents: number;
  amount_display: string;
  expires_at: string;
  distance_km?: number;
  pricing_breakdown?: Array<{ code: string; label: string; amount_cents: number }>;
};

export type BookingStartResult = {
  quote_id: string;
  state: string;
  customer_id: string;
  checkout_url: string | null;
  mock_checkout: boolean;
};

export type BookingConfirmation = {
  tracking_number: string;
  order_number: string;
  booking_number: string;
  amount_cents: number;
  state: string;
};

export type OrderResult = {
  order_id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string;
  pickup: AddressPayload;
  dropoff: AddressPayload;
};

export type TrackingEta = {
  source?: string;
  duration_seconds?: number;
  distance_meters?: number;
  polyline?: string;
  arrives_at?: string;
  label?: string;
};

export type OrderLiveTracking = {
  order_id: string;
  tracking_number: string;
  state: string;
  fleetbase_order_id?: string | null;
  live_tracking?: {
    pickup?: AddressPayload;
    dropoff?: AddressPayload;
    driver_location?: { lat: number; lng: number };
    optimized_route?: {
      polyline?: string;
      source?: string;
      duration_seconds?: number;
      distance_meters?: number;
      polyline_encoding?: "google" | "valhalla";
    };
    eta?: TrackingEta | null;
    delivery_status?: {
      order_state?: string;
      label?: string;
      in_transit?: boolean;
      delivered?: boolean;
    };
    last_updated?: string;
  } | null;
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "request_failed");
  }
  return res.json();
}

export function formatCents(cents: number, currency = "CAD"): string {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export function createQuote(payload: {
  pickup: AddressPayload;
  dropoff: AddressPayload;
  vehicle_class: string;
  package_type: string;
  weight_kg?: number;
  dimensions?: string;
  scheduled_at: string;
  schedule_mode: "now" | "later";
}) {
  return apiFetch<QuoteResult>("/v1/quotes", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function getQuote(quoteId: string) {
  return apiFetch<
    QuoteResult & {
      pickup?: AddressPayload;
      dropoff?: AddressPayload;
      vehicle_class?: string;
      package_type?: string;
    }
  >(`/v1/quotes/${encodeURIComponent(quoteId)}`).then((raw) => ({
    quote_id:
      (raw as { quote_id?: string; id?: string }).quote_id ??
      (raw as { id?: string }).id ??
      quoteId,
    state: raw.state,
    amount_cents: raw.amount_cents,
    amount_display: raw.amount_display ?? formatCents(raw.amount_cents),
    expires_at: raw.expires_at,
    distance_km: raw.distance_km,
    pricing_breakdown: raw.pricing_breakdown,
    pickup: raw.pickup,
    dropoff: raw.dropoff,
    vehicle_class: raw.vehicle_class,
    package_type: raw.package_type,
  }));
}

export function startBooking(
  token: string,
  payload: {
    quote_id: string;
    email: string;
    phone: string;
    clerk_user_id: string;
    terms_accepted: boolean;
    privacy_accepted: boolean;
    dangerous_goods_confirmed: boolean;
    consent_at: string;
    checkout_channel?: "retail" | "customer";
  }
) {
  return apiFetch<BookingStartResult>("/v1/bookings", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ checkout_channel: "customer", ...payload }),
  });
}

export function mockCompleteCheckout(quoteId: string) {
  return apiFetch<BookingConfirmation>("/v1/bookings/mock-complete", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export type BookingConfirmationStatus = {
  status: "pending" | "ready" | "failed";
  confirmation?: BookingConfirmation;
};

export function syncBookingCheckout(quoteId: string) {
  return apiFetch<BookingConfirmationStatus>("/v1/bookings/sync-checkout", {
    method: "POST",
    body: JSON.stringify({ quote_id: quoteId }),
  });
}

export function getOrderByTracking(trackingNumber: string) {
  return apiFetch<OrderResult>(`/v1/orders/${encodeURIComponent(trackingNumber)}`);
}

export function getOrderLiveTracking(trackingNumber: string) {
  return apiFetch<OrderLiveTracking>(`/v1/orders/${encodeURIComponent(trackingNumber)}/tracking`);
}
