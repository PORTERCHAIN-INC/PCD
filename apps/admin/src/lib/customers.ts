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

export type CreateCustomerInput = {
  email: string;
  phone?: string | null;
  full_name?: string | null;
  send_invite?: boolean;
};

export type CreateCustomerResult = {
  id: string;
  email: string;
  phone: string | null;
  customer_reference: string | null;
  display_name: string;
  clerk_user_id: string | null;
  clerk_linked: boolean;
  identity_status: string;
  clerk_action: string | null;
  created: boolean;
  created_at: string | null;
};

export type CustomerInviteResult = {
  id: string;
  email: string;
  clerk_user_id: string | null;
  clerk_linked: boolean;
  identity_status: string;
  clerk_action: string | null;
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
  create: (t: string, body: CreateCustomerInput) =>
    adminFetch<CreateCustomerResult>(B, t, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  invite: (t: string, id: string) =>
    adminFetch<CustomerInviteResult>(`${B}/${id}/invite`, t, { method: "POST" }),
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

// --------------------------------------------------------------------------- Customers 360

export type Customer360 = {
  customer_id: string;
  name: string;
  email: string;
  phone: string | null;
  since: string | null;
  account: string;
  numbers: {
    orders: number;
    lifetime_value_cents: number;
    avg_order_cents: number;
    credit_balance_cents: number;
    avg_rating: number | null;
    low_ratings: number;
    first_attempt_rate: number | null;
  };
  last_order_at: string | null;
  churn: {
    status: string;
    flag: boolean;
    days_since_last: number | null;
    usual_interval_days: number | null;
    threshold_days?: number;
    rule?: string;
  };
  risk: Array<{ tracking_number: string; reasons: string[] }>;
  consent: {
    marketing: ConsentRow;
    reorder: ConsentRow;
    suppressed: boolean;
    bounced: boolean;
    deliverable: boolean;
  };
  privacy: { status: string; jobs: PrivacyJob[] };
};

export type ConsentRow = {
  granted: boolean;
  basis: string;
  at: string | null;
  source: string | null;
};

export type PrivacyJob = {
  id: string;
  reference: string;
  customer_id: string | null;
  status: "pending_review" | "executed" | "rejected";
  source: string;
  plan: {
    erase: Record<string, unknown>;
    keep: Record<string, unknown>;
    blockers: { active_deliveries: string[] };
    stripe_customer: boolean;
  };
  result: Record<string, unknown> | null;
  reviewer: string | null;
  review_note: string | null;
  due_at: string | null;
  executed_at: string | null;
  created_at: string | null;
};

export type TimelineItem = {
  at: string | null;
  kind: string;
  title: string;
  detail: string;
  ref: string;
};

export type BookingLinkDraft = {
  sent: false;
  to: string;
  subject: string;
  body: string;
  link: string;
  note: string;
};

const A = "/v1/admin";

export const customer360Api = {
  overview: (t: string, id: string) => adminFetch<Customer360>(`${B}/${id}/360`, t),
  timeline: (t: string, id: string) => adminFetch<TimelineItem[]>(`${B}/${id}/timeline`, t),
  addNote: (t: string, id: string, body: string) =>
    adminFetch<{ id: string }>(`${B}/${id}/notes`, t, {
      method: "POST",
      body: JSON.stringify({ body }),
    }),
  credit: (t: string, id: string, amount_cents: number, reason: string) =>
    adminFetch<{ balance_cents: number }>(`${B}/${id}/credit`, t, {
      method: "POST",
      body: JSON.stringify({ amount_cents, reason }),
    }),
  refund: (
    t: string,
    id: string,
    tracking_number: string,
    amount_cents: number | null,
    reason: string
  ) =>
    adminFetch<{ refund: { status: string; amount_cents: number }; refunded_total_cents: number }>(
      `${B}/${id}/refund`,
      t,
      { method: "POST", body: JSON.stringify({ tracking_number, amount_cents, reason }) }
    ),
  bookingLinkDraft: (t: string, id: string) =>
    adminFetch<BookingLinkDraft>(`${B}/${id}/booking-link-draft`, t, { method: "POST" }),
  privacyJobs: (t: string, status?: string) =>
    adminFetch<PrivacyJob[]>(
      `${A}/customer-care/privacy-jobs${status ? `?status=${status}` : ""}`,
      t
    ),
  approveJob: (t: string, jobId: string, note: string) =>
    adminFetch<PrivacyJob>(`${A}/customer-care/privacy-jobs/${jobId}/approve`, t, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  rejectJob: (t: string, jobId: string, note: string) =>
    adminFetch<PrivacyJob>(`${A}/customer-care/privacy-jobs/${jobId}/reject`, t, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  nudges: (t: string) =>
    adminFetch<{
      enabled: boolean;
      nudges: Array<{
        id: string;
        email: string | null;
        name: string | null;
        last_tracking: string | null;
        reason: string;
        created_at: string | null;
      }>;
    }>(`${A}/customer-care/nudges`, t),
  draftNudges: (t: string) =>
    adminFetch<{ drafted: number; enabled: boolean }>(`${A}/customer-care/nudges/draft`, t, {
      method: "POST",
    }),
  decideNudges: (t: string, ids: string[], approve: boolean) =>
    adminFetch<{ decided: number }>(`${A}/customer-care/nudges/decide`, t, {
      method: "POST",
      body: JSON.stringify({ ids, approve }),
    }),
};
