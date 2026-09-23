import { publicEnv } from "./env";

export type AddressPayload = {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
  postal?: string;
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
  vehicle_class?: string | null;
  booking_mode?: string | null;
  parcels?: Array<{ preset_label?: string }> | null;
  invoice_number?: string | null;
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
  company_name?: string | null;
  logo_url?: string | null;
  tracking_page_message?: string | null;
  vehicle_class?: string | null;
  booking_mode?: string | null;
  goods_summary?: string | null;
  declared_value_cents?: number | null;
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
    branding?: {
      company_name?: string | null;
      logo_url?: string | null;
      tracking_page_message?: string | null;
    } | null;
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

export type QuotePreview = {
  amount_cents: number;
  amount_display: string;
  distance_km?: number | null;
  included_km?: number | null;
  vehicle_class?: string;
  booking_mode?: string;
  parcel_count?: number;
  pricing_breakdown?: Array<{ code: string; label: string; amount_cents: number }>;
};

export function previewQuote(payload: Parameters<typeof createQuote>[0]) {
  return apiFetch<QuotePreview>("/v1/quotes/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createQuote(payload: {
  pickup: AddressPayload;
  dropoff: AddressPayload;
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
  special_instructions?: string;
  additional_stops?: AddressPayload[];
  promo_code?: string;
  scheduled_at: string;
  schedule_mode: "now" | "later";
  anonymous_session_id?: string;
  visitor_session_id?: string;
  tracking?: Record<string, unknown>;
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
      booking_mode?: string | null;
      parcels?: Array<Record<string, unknown>> | null;
      declared_value_cents?: number | null;
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
    booking_mode: raw.booking_mode,
    parcels: raw.parcels,
    declared_value_cents: raw.declared_value_cents,
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
    anonymous_session_id?: string;
  }
) {
  return apiFetch<BookingStartResult>("/v1/bookings", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "customer" },
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
