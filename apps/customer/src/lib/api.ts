import { publicEnv } from "./env";

export const API_BASE = publicEnv.porterchainApiUrl;

export interface CustomerOrderSummary {
  order_id: string;
  order_number?: string;
  tracking_number: string;
  state: string;
  amount_cents?: number;
  currency?: string;
  scheduled_at?: string;
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  created_at?: string;
  vehicle_class?: string | null;
  booking_mode?: string | null;
  goods_summary?: string | null;
  declared_value_cents?: number | null;
}

export interface CustomerBookingSummary {
  booking_id: string;
  booking_number?: string;
  state: string;
  quote_id?: string | null;
  order_id?: string | null;
  created_at?: string;
}

export interface CustomerInvoiceSummary {
  invoice_id: string;
  invoice_number: string;
  order_id?: string | null;
  amount_cents: number;
  currency: string;
  status?: string;
  stripe_receipt_url?: string | null;
  pdf_url?: string | null;
  created_at?: string;
}

export interface CustomerInvoiceLine {
  description: string;
  order_number?: string | null;
  amount_cents: number;
  tax_cents: number;
}

export interface CustomerInvoiceDetail extends CustomerInvoiceSummary {
  receipt_number?: string | null;
  tax_cents: number;
  fees_cents: number;
  outstanding_cents: number;
  payment_terms?: string | null;
  due_date?: string | null;
  order_number?: string | null;
  tracking_number?: string | null;
  merchant_name?: string | null;
  pickup?: Record<string, unknown> | null;
  dropoff?: Record<string, unknown> | null;
  lines: CustomerInvoiceLine[];
}

export interface CustomerPaymentSummary {
  payment_id: string;
  status: string;
  amount_cents: number;
  currency: string;
}

export interface CustomerDashboard {
  active_order: CustomerOrderSummary | null;
  orders: CustomerOrderSummary[];
  bookings: CustomerBookingSummary[];
  invoices: CustomerInvoiceSummary[];
  payments: CustomerPaymentSummary[];
  stats: {
    total_orders?: number;
    total_bookings?: number;
    [key: string]: unknown;
  };
}

export interface CustomerSupportTicket {
  ticket_id: string;
  status: string;
  subject: string;
  description?: string | null;
  order_id?: string | null;
  created_at: string;
}

export interface CustomerRebookPayload {
  pickup: Record<string, unknown>;
  dropoff: Record<string, unknown>;
  vehicle_class: string | null;
  source_order_id: string;
  tracking_number: string;
}

export interface CustomerPrivacyDeleteResponse {
  reference: string;
  status: string;
  sla_days: number;
  message: string;
}

export const REBOOK_STORAGE_KEY = "porterchain_customer_rebook";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

function authHeaders(token: string): HeadersInit {
  return { Authorization: `Bearer ${token}`, "X-Porterchain-Portal": "customer" };
}

export const customerApi = {
  dashboard: (token: string) =>
    apiFetch<CustomerDashboard>("/v1/customers/me/dashboard", {
      headers: authHeaders(token),
    }),
  listSupport: (token: string) =>
    apiFetch<CustomerSupportTicket[]>("/v1/customers/me/support", {
      headers: authHeaders(token),
    }),
  createSupport: (
    token: string,
    body: { subject: string; description?: string; order_id?: string }
  ) =>
    apiFetch<CustomerSupportTicket>("/v1/customers/me/support", {
      method: "POST",
      headers: authHeaders(token),
      body: JSON.stringify(body),
    }),
  rebook: (token: string, orderId: string) =>
    apiFetch<CustomerRebookPayload>(`/v1/customers/me/rebook/${orderId}`, {
      method: "POST",
      headers: authHeaders(token),
    }),
  privacyExport: (token: string) =>
    apiFetch<Record<string, unknown>>("/v1/customers/me/privacy/export", {
      headers: authHeaders(token),
    }),
  privacyDeleteRequest: (token: string) =>
    apiFetch<CustomerPrivacyDeleteResponse>("/v1/customers/me/privacy/delete-request", {
      method: "POST",
      headers: authHeaders(token),
    }),
  invoices: (token: string) =>
    apiFetch<CustomerInvoiceSummary[]>("/v1/customers/me/invoices", {
      headers: authHeaders(token),
    }),
  invoice: (token: string, invoiceId: string) =>
    apiFetch<CustomerInvoiceDetail>(`/v1/customers/me/invoices/${invoiceId}`, {
      headers: authHeaders(token),
    }),
  downloadInvoicePdf: async (token: string, invoiceId: string, filename: string) => {
    const res = await fetch(`${API_BASE}/v1/customers/me/invoices/${invoiceId}/pdf`, {
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error("Could not download that invoice PDF.");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  },
};
