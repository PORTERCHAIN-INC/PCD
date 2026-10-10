import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type TaxSummary = {
  subtotal_cents: number;
  tax_cents: number;
  fees_cents: number;
  total_cents: number;
  invoice_count: number;
  currency: string;
};

export type ContractPricing = {
  has_contract: boolean;
  contract_id?: string | null;
  contract_name?: string | null;
  minimum_monthly_commitment_cents: number;
  rules: Record<string, unknown>;
  pricing_config: Record<string, unknown>;
  effective_from?: string | null;
  effective_to?: string | null;
};

export type BillingOverview = {
  payment_terms: string;
  billing_cycle: string;
  billing_cycles_available: string[];
  net_terms_days: number;
  credit_limit_cents?: number | null;
  available_credit_cents?: number | null;
  headroom_cents?: number | null;
  credits_applied_cents?: number;
  /** Overpayment credit carried to the next invoice. */
  credit_balance_cents?: number;
  glossary?: Array<{ term: string; meaning: string }>;
  remittance?: {
    payee: string;
    advice_email?: string | null;
    memo: string;
    open_invoice_numbers: string[];
    outstanding_cents: number;
    credits_applied_cents: number;
    net_terms_days: number;
    instructions: string;
    /** Merchants pay by Interac e-Transfer only. */
    method?: "interac" | string;
    etransfer_email?: string | null;
    /** PC-XXXXX codes to type in the e-Transfer message. */
    open_references?: string[];
  } | null;
  outstanding_balance_cents: number;
  outstanding_invoices_cents: number;
  uninvoiced_orders_cents: number;
  credit_notes_cents?: number;
  overdue_cents?: number;
  open_invoice_count?: number;
  overdue_invoice_count?: number;
  monthly_orders: number;
  monthly_spend_cents: number;
  period_start?: string;
  period_end?: string;
  invoices_due: number;
  overdue_invoices: number;
  invoice_count: number;
  payment_count: number;
  credit_notes_count: number;
  tax_summary: TaxSummary;
  contract_pricing: ContractPricing;
};

export type InvoiceRow = {
  invoice_id: string;
  invoice_number: string;
  order_id: string;
  order_number?: string | null;
  tracking_number?: string | null;
  amount_cents: number;
  tax_cents: number;
  outstanding_cents: number;
  currency: string;
  status: string;
  payment_terms: string;
  due_date?: string | null;
  last_reminded_at?: string | null;
  created_at: string;
  pdf_url?: string | null;
  stripe_receipt_url?: string | null;
};

export type InvoiceDetailLine = {
  line_id?: string | null;
  order_id?: string | null;
  order_number?: string | null;
  tracking_number?: string | null;
  description: string;
  amount_cents: number;
  tax_cents: number;
  channel?: string | null;
  pricing_model?: string | null;
  quote_breakdown?: Record<string, unknown> | null;
  rate_quote_id?: string | null;
  rate_quote_cents?: number | null;
};

export type InvoiceDetail = {
  invoice_id: string;
  invoice_number: string;
  status: string;
  payment_terms: string;
  due_date?: string | null;
  aging_bucket?: string | null;
  amount_cents: number;
  tax_cents: number;
  fees_cents: number;
  outstanding_cents: number;
  currency: string;
  created_at: string;
  pdf_url?: string | null;
  remittance_memo?: string | null;
  lines: InvoiceDetailLine[];
  lines_total_cents?: number;
};

export type PaymentRow = {
  payment_id: string;
  order_id: string;
  order_number?: string | null;
  amount_cents: number;
  currency: string;
  status: string;
  payment_method?: string | null;
  payment_reference?: string | null;
  receipt_url?: string | null;
  created_at?: string | null;
};

export type CreditNoteRow = {
  credit_note_id: string;
  order_id?: string | null;
  order_number?: string | null;
  amount_cents?: number | null;
  reason?: string | null;
  status: string;
  created_at?: string | null;
};

export type BillingHistoryRow = {
  kind: string;
  id: string;
  reference?: string | null;
  description: string;
  amount_cents: number;
  status?: string | null;
  occurred_at?: string | null;
};

export type StatementDetail = BillingOverview & {
  line_items: Array<Record<string, unknown>>;
  line_items_total_cents: number;
};

async function billingFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  if (rest.body && !(rest.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...rest,
      headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
    });
  } catch {
    throw new Error(
      "Could not reach PorterChain billing. Check your connection and try again — if this continues, contact PorterChain support."
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(
      typeof detail === "string" ? detail : `Could not load billing (${response.status})`
    );
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

async function billingDownload(path: string, token: string, orgId?: string, filename?: string) {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  const response = await fetch(`${API_BASE}${path}`, {
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = (body as { detail?: unknown }).detail;
    throw new Error(typeof detail === "string" ? detail : "Could not download that file.");
  }
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename || "export.csv";
  a.click();
  URL.revokeObjectURL(url);
}

export const billingApi = {
  overview: (token: string, orgId?: string) =>
    billingFetch<BillingOverview>("/v1/merchant/billing/overview", token, { orgId }),

  statementDetail: (token: string, orgId?: string) =>
    billingFetch<StatementDetail>("/v1/merchant/billing/statement/detail", token, { orgId }),

  invoices: (token: string, orgId?: string) =>
    billingFetch<InvoiceRow[]>("/v1/merchant/billing/invoices", token, { orgId }),

  payments: (token: string, orgId?: string) =>
    billingFetch<PaymentRow[]>("/v1/merchant/billing/payments", token, { orgId }),

  creditNotes: (token: string, orgId?: string) =>
    billingFetch<CreditNoteRow[]>("/v1/merchant/billing/credit-notes", token, { orgId }),

  history: (token: string, orgId?: string) =>
    billingFetch<BillingHistoryRow[]>("/v1/merchant/billing/history", token, { orgId }),

  taxSummary: (token: string, orgId?: string) =>
    billingFetch<TaxSummary>("/v1/merchant/billing/tax-summary", token, { orgId }),

  contract: (token: string, orgId?: string) =>
    billingFetch<ContractPricing>("/v1/merchant/billing/contract", token, { orgId }),

  rateCard: (token: string, orgId?: string) =>
    billingFetch<import("@/lib/rate-card").MerchantRateCard>(
      "/v1/merchant/pricing/rate-card",
      token,
      { orgId }
    ),

  invoicePdfUrl: (invoiceId: string) => `${API_BASE}/v1/merchant/billing/invoices/${invoiceId}/pdf`,

  downloadInvoicePdf: (token: string, invoiceId: string, orgId?: string, filename?: string) =>
    billingDownload(
      `/v1/merchant/billing/invoices/${invoiceId}/pdf`,
      token,
      orgId,
      filename || `invoice-${invoiceId}.pdf`
    ),

  remindInvoice: (token: string, invoiceId: string, orgId?: string) =>
    billingFetch<{
      invoice_id: string;
      invoice_number: string;
      email: string;
      pay_url?: string | null;
      last_reminded_at: string | null;
    }>(`/v1/merchant/billing/invoices/${invoiceId}/remind`, token, {
      method: "POST",
      orgId,
    }),

  invoiceDetail: (token: string, invoiceId: string, orgId?: string) =>
    billingFetch<InvoiceDetail>(`/v1/merchant/billing/invoices/${invoiceId}`, token, { orgId }),

  downloadInvoicesCsv: (token: string, orgId?: string) =>
    billingDownload("/v1/merchant/billing/export/invoices.csv", token, orgId, "invoices.csv"),

  downloadStatementCsv: (token: string, orgId?: string) =>
    billingDownload("/v1/merchant/billing/export/statement.csv", token, orgId, "statement.csv"),

  /** Account statement PDF: balance, PC codes, e-Transfer instructions, open invoices. */
  downloadStatementPdf: (token: string, orgId?: string) =>
    billingDownload(
      "/v1/merchant/billing/statement.pdf",
      token,
      orgId,
      "porterchain-statement.pdf"
    ),

  downloadHistoryCsv: (token: string, orgId?: string) =>
    billingDownload("/v1/merchant/billing/export/history.csv", token, orgId, "billing-history.csv"),

  codStatus: (token: string, orgId?: string) =>
    billingFetch<{
      cod_enabled: boolean;
      stripe_connect_account_id: string | null;
      connect_ready: boolean;
    }>("/v1/merchant/billing/cod", token, { orgId }),

  codConnect: (token: string, orgId?: string) =>
    billingFetch<{ url: string; account_id: string; mock?: string }>(
      "/v1/merchant/billing/cod/connect",
      token,
      { method: "POST", orgId }
    ),

  codEnable: (token: string, enabled: boolean, orgId?: string) =>
    billingFetch<{ cod_enabled: boolean; stripe_connect_account_id: string | null }>(
      "/v1/merchant/billing/cod/enable",
      token,
      { method: "POST", orgId, body: JSON.stringify({ enabled }) }
    ),
};

export function formatTerms(terms: string) {
  return terms.replace(/_/g, " ").replace(/\bnet\b/i, "Net");
}

export function formatCycle(cycle: string) {
  return cycle.charAt(0) + cycle.slice(1).toLowerCase();
}

export const STATUS_STYLES: Record<string, string> = {
  paid: "bg-green-100 text-green-800",
  sent: "bg-blue-100 text-blue-800",
  pending: "bg-amber-100 text-amber-900",
  overdue: "bg-red-100 text-red-800",
  cancelled: "bg-gray-100 text-gray-600",
  void: "bg-gray-100 text-gray-600",
  uninvoiced: "bg-violet-100 text-violet-800",
};
