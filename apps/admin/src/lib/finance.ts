import { z } from "zod";
import { adminFetch } from "@/lib/api";
import { downloadCsv, toCsv } from "@/lib/crmFormat";

export const INVOICE_STATUSES = [
  "draft",
  "pending",
  "sent",
  "paid",
  "partially_paid",
  "overdue",
  "cancelled",
  "void",
] as const;

const invoiceSchema = z.object({
  invoice_id: z.string(),
  invoice_number: z.string(),
  receipt_number: z.string().nullable().optional(),
  status: z.string(),
  merchant_id: z.string().nullable().optional(),
  merchant_name: z.string().nullable().optional(),
  customer_id: z.string().nullable().optional(),
  customer_email: z.string().nullable().optional(),
  order_id: z.string(),
  order_number: z.string().nullable().optional(),
  tracking_number: z.string().nullable().optional(),
  booking_number: z.string().nullable().optional(),
  amount_cents: z.number(),
  tax_cents: z.number(),
  fees_cents: z.number(),
  outstanding_cents: z.number(),
  currency: z.string(),
  payment_terms: z.string(),
  due_date: z.string().nullable().optional(),
  pdf_url: z.string().nullable().optional(),
  receipt_url: z.string().nullable().optional(),
  created_at: z.string(),
  last_reminded_at: z.string().nullable().optional(),
});

export type InvoiceRow = z.infer<typeof invoiceSchema>;

/** Who to phone about an unpaid invoice — the merchant's primary AP contact (BL). */
const apContactSchema = z.object({
  name: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  phone: z.string().nullable().optional(),
  role: z.string().nullable().optional(),
  is_primary: z.boolean().optional(),
  /** "company" means no AP contact is on file and these are the company's own details. */
  source: z.string().optional(),
});

export type ApContact = z.infer<typeof apContactSchema>;

const collectionSchema = invoiceSchema.extend({
  days_overdue: z.number(),
  aging_bucket: z.string(),
  ap_contact: apContactSchema.nullable().optional(),
});

export type CollectionRow = z.infer<typeof collectionSchema>;

export const invoiceDetailSchema = invoiceSchema.extend({
  payment: z.record(z.string(), z.unknown()).nullable().optional(),
  timeline: z.array(z.record(z.string(), z.unknown())),
  audit_log: z.array(z.record(z.string(), z.unknown())),
  duplicates: z.array(z.record(z.string(), z.unknown())),
  quote_id: z.string().nullable().optional(),
  quote_amount_cents: z.number().nullable().optional(),
  pricing_breakdown: z.record(z.string(), z.unknown()).nullable().optional(),
  pricing_model: z.string().nullable().optional(),
  pricing_metadata: z.record(z.string(), z.unknown()).optional(),
});

export type InvoiceDetail = z.infer<typeof invoiceDetailSchema>;

const paymentSchema = z.object({
  payment_id: z.string(),
  status: z.string(),
  amount_cents: z.number(),
  currency: z.string(),
  payment_method: z.string(),
  stripe_payment_intent_id: z.string().nullable().optional(),
  payment_reference: z.string().nullable().optional(),
  transaction_id: z.string().nullable().optional(),
  order_id: z.string().nullable().optional(),
  order_number: z.string().nullable().optional(),
  tracking_number: z.string().nullable().optional(),
  customer_email: z.string().nullable().optional(),
  receipt_url: z.string().nullable().optional(),
  failure_reason: z.string().nullable().optional(),
  created_at: z.string(),
});

export type PaymentRow = z.infer<typeof paymentSchema>;

const payoutSchema = z.object({
  payout_id: z.string(),
  driver_id: z.string(),
  driver_name: z.string().nullable().optional(),
  amount_cents: z.number(),
  currency: z.string(),
  status: z.string(),
  reference: z.string().nullable().optional(),
  created_at: z.string(),
});

export type PayoutRow = z.infer<typeof payoutSchema>;

export type FinanceDashboard = {
  today_revenue_cents: number;
  month_revenue_cents: number;
  outstanding_invoices_cents: number;
  paid_invoices_cents: number;
  outstanding_invoice_count: number;
  paid_invoice_count: number;
  pending_payments: number;
  paid_payments_count: number;
  refunds_count: number;
  credit_notes_count: number;
  merchant_balances_cents: number;
  driver_payouts_pending_cents: number;
  driver_payouts_paid_cents: number;
  driver_wallets_cents: number;
  taxes_collected_cents: number;
  profit_estimate_cents: number;
  payment_success_rate: number;
  overdue_invoices_count: number;
  revenue_trend: Array<{ date: string; revenue_cents: number }>;
  cash_flow_cents: number;
  top_merchants: Array<{ name: string; revenue_cents: number }>;
  revenue_forecast_cents: number;
};

export type FinanceListPage<T> = {
  items: T[];
  total: number;
  limit: number;
  offset: number;
};

export type FinanceFilters = {
  status?: string;
  merchant_id?: string;
  currency?: string;
  search?: string;
  outstanding_only?: boolean;
  limit?: number;
  offset?: number;
};

const B = "/v1/admin/finance";

function qs(filters?: FinanceFilters): string {
  if (!filters) return "";
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const financeApi = {
  dashboard: (token: string) => adminFetch<FinanceDashboard>(`${B}/dashboard`, token),
  reports: (token: string) => adminFetch<Record<string, unknown>>(`${B}/reports`, token),
  collections: async (token: string) => {
    const raw = await adminFetch<unknown[]>(`${B}/collections`, token);
    return z.array(collectionSchema).parse(raw);
  },
  exportGl: (token: string) => adminFetch<Array<Record<string, unknown>>>(`${B}/export`, token),
  invoices: async (token: string, filters?: FinanceFilters) => {
    const raw = await adminFetch<unknown>(`${B}/invoices${qs(filters)}`, token);
    return z
      .object({
        items: z.array(invoiceSchema),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
      })
      .parse(raw);
  },
  invoiceDetail: async (token: string, id: string) => {
    const raw = await adminFetch<unknown>(`${B}/invoices/${id}`, token);
    return invoiceDetailSchema.parse(raw);
  },
  payments: async (token: string, status?: string, page?: { limit?: number; offset?: number }) => {
    const p = new URLSearchParams();
    if (status) p.set("status", status);
    if (page?.limit != null) p.set("limit", String(page.limit));
    if (page?.offset != null) p.set("offset", String(page.offset));
    const q = p.toString() ? `?${p.toString()}` : "";
    const raw = await adminFetch<unknown>(`${B}/payments${q}`, token);
    return z
      .object({
        items: z.array(paymentSchema),
        total: z.number(),
        limit: z.number(),
        offset: z.number(),
      })
      .parse(raw);
  },
  payouts: async (token: string, status?: string) => {
    const q = status ? `?status=${status}` : "";
    const raw = await adminFetch<unknown[]>(`${B}/payouts${q}`, token);
    return z.array(payoutSchema).parse(raw);
  },
  ledger: (token: string) => adminFetch<Array<Record<string, unknown>>>(`${B}/ledger`, token),
  creditNote: (token: string, body: { order_id: string; amount_cents: number; reason: string }) =>
    adminFetch<{ ledger_id: string }>(`${B}/credit-notes`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  merchantArPreview: (
    token: string,
    params: { merchant_id: string; period_start?: string; period_end?: string }
  ) => {
    const p = new URLSearchParams({ merchant_id: params.merchant_id });
    if (params.period_start) p.set("period_start", params.period_start);
    if (params.period_end) p.set("period_end", params.period_end);
    return adminFetch<{
      merchant_id: string;
      merchant_name: string | null;
      payment_terms: string | null;
      billing_cycle: string | null;
      period_start: string;
      period_end: string;
      order_count: number;
      uninvoiced_cents: number;
      order_ids: string[];
      orders: Array<{
        order_id: string;
        order_number: string;
        tracking_number: string;
        state: string;
        amount_cents: number;
      }>;
    }>(`${B}/merchant-ar/preview?${p.toString()}`, token);
  },
  merchantArGenerate: (
    token: string,
    body: { merchant_id: string; period_start?: string; period_end?: string }
  ) =>
    adminFetch<{
      merchant_id: string;
      period_start: string;
      period_end: string;
      created_count: number;
      skipped_count: number;
      invoices: Array<{
        invoice_id: string;
        invoice_number: string;
        order_id: string;
        amount_cents: number;
      }>;
    }>(`${B}/merchant-ar/generate`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  recordPayment: (
    token: string,
    invoiceId: string,
    body: { method: string; amount_cents?: number; reference?: string }
  ) =>
    adminFetch<{
      invoice_id: string;
      payment_id: string;
      amount_cents: number;
      status: string;
      method: string;
    }>(`${B}/invoices/${invoiceId}/record-payment`, token, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  remindInvoice: (token: string, invoiceId: string) =>
    adminFetch<{
      invoice_id: string;
      invoice_number: string;
      email: string;
      last_reminded_at: string | null;
    }>(`${B}/invoices/${invoiceId}/remind`, token, { method: "POST" }),
};

export const INVOICE_STATUS_STYLES: Record<string, string> = {
  draft: "bg-gray-100 text-gray-600",
  pending: "bg-amber-100 text-amber-800",
  sent: "bg-blue-100 text-blue-700",
  paid: "bg-green-100 text-green-700",
  partially_paid: "bg-teal-100 text-teal-800",
  overdue: "bg-red-100 text-red-700",
  cancelled: "bg-gray-100 text-gray-500",
  void: "bg-gray-100 text-gray-500",
};

export const PAYMENT_STATUS_STYLES: Record<string, string> = {
  SUCCEEDED: "bg-green-100 text-green-700",
  PROCESSING: "bg-amber-100 text-amber-700",
  PENDING: "bg-gray-100 text-gray-600",
  FAILED: "bg-red-100 text-red-700",
  REFUNDED: "bg-orange-100 text-orange-800",
};

export function exportInvoicesCsv(rows: InvoiceRow[], filename = "invoices.csv") {
  const headers = [
    "invoice_number",
    "status",
    "merchant_name",
    "customer_email",
    "order_number",
    "tracking_number",
    "amount_cents",
    "outstanding_cents",
    "currency",
    "created_at",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) =>
      headers
        .map((h) => {
          const v = r[h as keyof InvoiceRow];
          const s = v == null ? "" : String(v);
          return s.includes(",") ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(",")
    ),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** The aging report a collector works from, contact details included (BL). */
export function exportCollectionsCsv(rows: CollectionRow[], filename = "collections-aging.csv") {
  const headers = [
    "invoice_number",
    "merchant_name",
    "due_date",
    "days_overdue",
    "aging_bucket",
    "outstanding_cents",
    "payment_terms",
    "ap_contact_name",
    "ap_contact_phone",
    "ap_contact_email",
  ];
  const body = rows.map((r) => [
    r.invoice_number,
    r.merchant_name ?? "",
    (r.due_date ?? "").slice(0, 10),
    String(r.days_overdue),
    r.aging_bucket,
    String(r.outstanding_cents),
    r.payment_terms,
    r.ap_contact?.name ?? "",
    r.ap_contact?.phone ?? "",
    r.ap_contact?.email ?? "",
  ]);
  downloadCsv(filename, toCsv(headers, body));
}

export function exportGlCsv(rows: Array<Record<string, unknown>>, filename = "general-ledger.csv") {
  const headers = [
    "date",
    "type",
    "reference",
    "description",
    "debit_cents",
    "credit_cents",
    "tax_cents",
    "currency",
  ];
  const lines = [
    headers.join(","),
    ...rows.map((r) => headers.map((h) => String(r[h] ?? "")).join(",")),
  ];
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
