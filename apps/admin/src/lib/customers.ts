import { adminFetch } from "@/lib/api";

export type CustomerRow = {
  id: string;
  email: string;
  phone: string | null;
  customer_reference: string | null;
  display_name: string;
  clerk_user_id: string | null;
  clerk_linked: boolean;
  identity_status: string;
  stripe_customer_id?: string | null;
  privacy_status: string | null;
  privacy_hold_reference: string | null;
  privacy_hold_at?: string | null;
  lifetime_orders: number;
  lifetime_revenue_cents: number;
  open_support_tickets: number;
  open_claims?: number;
  last_order_at?: string | null;
  created_at: string | null;
};

export type CustomerDetail = CustomerRow & {
  recent_orders: Array<{
    order_id: string;
    order_number: string;
    tracking_number: string;
    state: string;
    amount_cents: number;
  }>;
  settings_users_href?: string;
};

export type CustomerOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string | null;
  created_at: string | null;
};

export type CustomerStats = {
  total: number;
  clerk_linked: number;
  orphan: number;
  dsr_hold: number;
  orders_30d: number;
  revenue_30d_cents: number;
};

export type CustomerInvoice = {
  id: string;
  invoice_number: string;
  receipt_number: string | null;
  order_id: string;
  amount_cents: number;
  tax_cents: number;
  fees_cents: number;
  currency: string;
  stripe_receipt_url: string | null;
  pdf_url: string | null;
  due_at: string | null;
  created_at: string | null;
};

export type CustomerPayment = {
  id: string;
  order_id: string | null;
  status: string;
  amount_cents: number;
  currency: string;
  payment_method: string | null;
  payment_reference: string | null;
  stripe_payment_intent_id: string | null;
  receipt_url: string | null;
  created_at: string | null;
};

export type CustomerCare = {
  open_support_tickets: number;
  open_claims: number;
  support_tickets: Array<{
    id: string;
    subject: string;
    status: string;
    priority: string | null;
    created_at: string | null;
  }>;
  claims: Array<{
    id: string;
    order_id: string;
    claim_type: string;
    status: string;
    description: string | null;
    created_at: string | null;
    resolved_at: string | null;
  }>;
};

export type CustomerListParams = {
  search?: string;
  clerk_linked?: string;
  privacy_status?: string;
  limit?: string;
};

export type CustomerAddressInput = {
  formatted: string;
  place_id?: string | null;
  lat?: number | null;
  lng?: number | null;
};

export type CreateCustomerBookingDraftInput = {
  pickup: CustomerAddressInput;
  dropoff: CustomerAddressInput;
  vehicle_class: string;
  package_type?: string;
  weight_kg?: number | null;
  dimensions?: string | null;
  declared_value_cents?: number | null;
  special_instructions?: string | null;
  scheduled_at: string;
  schedule_mode?: string;
  send_payment_link?: boolean;
};

export type CreateCustomerBookingDraftResult = {
  draft_id: string;
  draft_number: string | null;
  quote_id: string;
  customer_id: string;
  amount_cents: number;
  currency: string;
  state: string;
  checkout_url: string | null;
  payment_id: string | null;
  stripe_checkout_session_id: string | null;
};

export type CustomerPaymentLinkResult = {
  checkout_url: string | null;
  payment_id: string | null;
  stripe_checkout_session_id: string | null;
};

const B = "/v1/admin/customers";

const qs = (params: Record<string, string | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) s.set(k, v);
  const out = s.toString();
  return out ? `?${out}` : "";
};

export const customersApi = {
  stats: (t: string) => adminFetch<CustomerStats>(`${B}/stats`, t),
  list: (t: string, params: CustomerListParams = {}) =>
    adminFetch<CustomerRow[]>(`${B}${qs(params)}`, t),
  detail: (t: string, id: string) => adminFetch<CustomerDetail>(`${B}/${id}`, t),
  orders: (t: string, id: string, params: { limit?: number; state?: string } = {}) =>
    adminFetch<CustomerOrder[]>(
      `${B}/${id}/orders${qs({
        limit: params.limit != null ? String(params.limit) : "50",
        state: params.state,
      })}`,
      t
    ),
  invoices: (t: string, id: string, limit = 50) =>
    adminFetch<CustomerInvoice[]>(`${B}/${id}/invoices?limit=${limit}`, t),
  payments: (t: string, id: string, limit = 50) =>
    adminFetch<CustomerPayment[]>(`${B}/${id}/payments?limit=${limit}`, t),
  care: (t: string, id: string, limit = 20) =>
    adminFetch<CustomerCare>(`${B}/${id}/care?limit=${limit}`, t),
  createBookingDraft: (t: string, id: string, body: CreateCustomerBookingDraftInput) =>
    adminFetch<CreateCustomerBookingDraftResult>(`${B}/${id}/booking-drafts`, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  sendDraftPaymentLink: (t: string, id: string, draftId: string) =>
    adminFetch<CustomerPaymentLinkResult>(
      `${B}/${id}/booking-drafts/${draftId}/send-payment-link`,
      t,
      { method: "POST" }
    ),
};
