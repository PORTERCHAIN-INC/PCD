import { publicEnv } from "@/lib/env";
import type { BookDeliveryPayload } from "@/lib/api";

const API_BASE = publicEnv.porterchainApiUrl;

async function bookingFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (!(init?.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
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

export interface BookingPreview {
  valid: boolean;
  amount_cents?: number;
  currency?: string;
  vehicle_class?: string;
  vehicle_recommendation?: {
    recommended_vehicle: string;
    preferred_vehicles: string[];
    alternatives: string[];
  };
  contract_pricing?: boolean;
  contract_id?: string | null;
  payment_terms?: string | null;
  warnings?: string[];
  pricing_breakdown?: Record<string, unknown>;
  distance_meters?: number;
  estimated_duration_minutes?: number;
  address_errors?: Array<{ field: string; error: string; hint?: string }>;
  error?: string;
  message?: string;
}

export interface BookingDraft {
  draft_id: string;
  state: string;
  current_step?: string;
  pickup?: Record<string, unknown>;
  dropoff?: Record<string, unknown>;
  vehicle_class?: string;
  package_type?: string;
  weight_kg?: number;
  dimensions?: string;
  special_instructions?: string;
  amount_cents?: number;
  pricing_breakdown?: Record<string, unknown>;
  merchant_meta?: Record<string, unknown>;
  expires_at?: string;
}

export interface BookingTemplate {
  id: string;
  name: string;
  payload: Record<string, unknown>;
  is_recurring: boolean;
  recurrence_rule?: string | null;
  created_at: string;
}

export interface SavedAddress {
  id: string;
  label: string;
  address_type: string;
  formatted: string;
  is_default: boolean;
}

export interface Recipient {
  id: string;
  name: string;
  email?: string | null;
  phone?: string | null;
  company?: string | null;
}

export interface BookingConfirmResult {
  order_id: string;
  order_number: string;
  tracking_number: string;
  amount_cents: number;
  preview: BookingPreview;
}

export function previewBooking(token: string, payload: BookDeliveryPayload, orgId?: string) {
  return bookingFetch<BookingPreview>("/v1/merchant/booking/preview", token, {
    method: "POST",
    body: JSON.stringify(payload),
    orgId,
  });
}

export function confirmBooking(
  token: string,
  booking: BookDeliveryPayload,
  orgId?: string,
  draftId?: string
) {
  return bookingFetch<BookingConfirmResult>("/v1/merchant/booking/confirm", token, {
    method: "POST",
    body: JSON.stringify({ booking, draft_id: draftId }),
    orgId,
  });
}

export function saveBookingDraft(
  token: string,
  payload: BookDeliveryPayload,
  orgId?: string,
  currentStep = "review"
) {
  return bookingFetch<{ draft_id: string; state: string; preview: BookingPreview }>(
    `/v1/merchant/booking/draft?current_step=${encodeURIComponent(currentStep)}`,
    token,
    { method: "POST", body: JSON.stringify(payload), orgId }
  );
}

export function getActiveDraft(token: string, orgId?: string) {
  return bookingFetch<BookingDraft | null>("/v1/merchant/booking/draft", token, { orgId });
}

export function listBookingTemplates(token: string, orgId?: string) {
  return bookingFetch<BookingTemplate[]>("/v1/merchant/booking/templates", token, { orgId });
}

export function createBookingTemplate(
  token: string,
  name: string,
  payload: Record<string, unknown>,
  orgId?: string
) {
  return bookingFetch<BookingTemplate>("/v1/merchant/booking/templates", token, {
    method: "POST",
    body: JSON.stringify({ name, payload }),
    orgId,
  });
}

export function deleteBookingTemplate(token: string, templateId: string, orgId?: string) {
  return bookingFetch<void>(`/v1/merchant/booking/templates/${templateId}`, token, {
    method: "DELETE",
    orgId,
  });
}

export function listSavedAddresses(token: string, orgId?: string) {
  return bookingFetch<SavedAddress[]>("/v1/merchant/booking/saved-addresses", token, { orgId });
}

export function listRecipients(token: string, orgId?: string) {
  return bookingFetch<Recipient[]>("/v1/merchant/booking/recipients", token, { orgId });
}

export function confirmMultiParcel(
  token: string,
  pickup: BookDeliveryPayload["pickup"],
  parcels: BookDeliveryPayload[],
  orgId?: string
) {
  return bookingFetch<{
    orders: Array<{ parcel: number; order_id: string; tracking_number: string; amount_cents: number }>;
    errors: Array<{ parcel: number; error: string }>;
    total_amount_cents: number;
  }>("/v1/merchant/booking/multi", token, {
    method: "POST",
    body: JSON.stringify({ pickup, parcels }),
    orgId,
  });
}

export function formatCents(cents: number, currency = "CAD") {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}
