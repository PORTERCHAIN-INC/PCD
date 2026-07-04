export type AddressPayload = {
  formatted: string;
  place_id?: string;
  lat?: number;
  lng?: number;
};

export type PricingLineItem = {
  code: string;
  label: string;
  amount_cents: number;
};

export type QuoteResult = {
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
};

export type CreateQuotePayload = {
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
};

export type StartBookingPayload = {
  quote_id: string;
  email: string;
  phone: string;
  clerk_user_id: string;
  anonymous_session_id?: string;
  terms_accepted?: boolean;
  privacy_accepted?: boolean;
  dangerous_goods_confirmed?: boolean;
  consent_at?: string;
};

export type BookingResult = {
  quote_id: string;
  state: string;
  customer_id: string;
  checkout_url: string | null;
  mock_checkout: boolean;
};

export type BookingConfirmationResult = {
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
};

export type BookingConfirmationStatus = {
  status: "processing" | "ready";
  confirmation: BookingConfirmationResult | null;
};

export type OrderResult = {
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
};

export type LiveTrackingPayload = {
  order_id: string;
  tracking_number: string;
  state: string;
  fleetbase_order_id?: string | null;
  live_tracking: {
    driver_location?: { lat: number; lng: number };
    eta_minutes?: number;
    status?: string;
    [key: string]: unknown;
  } | null;
};

export type CustomerDashboard = {
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
};

export type SupportTicket = {
  ticket_id: string;
  status: string;
  subject: string;
  description?: string | null;
  order_id?: string | null;
  created_at: string;
};

export type CreateSupportPayload = {
  subject: string;
  description?: string;
  order_id?: string;
};

export type RebookPayload = {
  pickup: AddressPayload;
  dropoff: AddressPayload;
  vehicle_class: string | null;
  source_order_id: string;
  tracking_number: string;
};

export type PaymentRetryResult = {
  payment_id: string;
  checkout_url: string | null;
  status: string;
};

export type BookingDraftResult = {
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
};

export type AuthMeResult = {
  user_id: string;
  user_type: string;
  roles: string[];
  permissions: string[];
  email?: string | null;
};
