import { z } from "zod";
import { adminFetch } from "@/lib/api";

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
  customer_id: z.string(),
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
});

export type InvoiceRow = z.infer<typeof invoiceSchema>;

export const invoiceDetailSchema = invoiceSchema.extend({
  payment: z.record(z.string(), z.unknown()).nullable().optional(),
  timeline: z.array(z.record(z.string(), z.unknown())),
  audit_log: z.array(z.record(z.string(), z.unknown())),
  duplicates: z.array(z.record(z.string(), z.unknown())),
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

export type FinanceFilters = {
  status?: string;
  merchant_id?: string;
  currency?: string;
  search?: string;
  outstanding_only?: boolean;
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
    return z.array(invoiceSchema).parse(raw);
  },
  exportGl: (token: string) => adminFetch<Array<Record<string, unknown>>>(`${B}/export`, token),
  invoices: async (token: string, filters?: FinanceFilters) => {
    const raw = await adminFetch<unknown[]>(`${B}/invoices${qs(filters)}`, token);
    return z.array(invoiceSchema).parse(raw);
  },
  invoiceDetail: async (token: string, id: string) => {
    const raw = await adminFetch<unknown>(`${B}/invoices/${id}`, token);
    return invoiceDetailSchema.parse(raw);
  },
  payments: async (token: string, status?: string) => {
    const q = status ? `?status=${status}` : "";
    const raw = await adminFetch<unknown[]>(`${B}/payments${q}`, token);
    return z.array(paymentSchema).parse(raw);
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
