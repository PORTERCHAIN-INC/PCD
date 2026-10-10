/** Round-2 Finance API: Cash, reminder drafts, Stripe recon, margin, tax, Driver Pay. */
import { adminFetch } from "@/lib/api";
import { downloadOrderFile } from "@/lib/orders";

const B = "/v1/admin/finance";

export type CashMerchant = {
  merchant_id: string;
  merchant_name: string;
  outstanding_cents: number;
  overdue_cents: number;
  invoice_count: number;
  oldest_days: number;
  buckets: Record<string, number>;
  references: string[];
  ap_contact?: { name?: string | null; email?: string | null; phone?: string | null } | null;
};

export type CreditHold = {
  merchant_id: string;
  merchant_name: string;
  blocked?: boolean;
  reasons?: string[];
};

export type CashBoard = {
  owed_cents: number;
  overdue_cents: number;
  merchant_count: number;
  buckets: Record<string, number>;
  bucket_order: string[];
  merchant_credit_cents: number;
  interac_open_count: number;
  interac_open_cents: number;
  draft_count: number;
  merchants: CashMerchant[];
  credit_holds: { available: boolean; source: string; items: CreditHold[] };
};

export type ReminderDraft = {
  id: string;
  merchant_id: string;
  merchant_name: string | null;
  to_email: string | null;
  subject: string;
  body: string;
  invoice_count: number;
  amount_cents: number;
  oldest_days: number;
  status: string;
};

export type StripePayoutRow = {
  id: string;
  stripe_payout_id: string;
  status: string;
  amount_cents: number;
  arrival_date: string | null;
  gross_cents: number | null;
  fee_cents: number | null;
  refund_cents: number | null;
  dispute_cents: number | null;
  matched_count: number | null;
  unmatched_count: number | null;
  difference_cents: number | null;
  reconciled: boolean;
};

export type StripeDispute = {
  id: string;
  dispute_id: string | null;
  status: string;
  open: boolean;
  amount_cents: number | null;
  reason: string | null;
  evidence_due_by: string | null;
  invoice_id: string | null;
};

export type StripeOverview = {
  payouts: StripePayoutRow[];
  disputes: StripeDispute[];
  open_disputes: number;
  open_dispute_cents: number;
  unreconciled: number;
  fees_cents_30d: number;
};

export type MarginRow = {
  route_id?: string;
  order_id?: string;
  order_number?: string;
  driver_id: string | null;
  day: string;
  stops?: number;
  revenue_cents: number;
  driver_cost_cents: number;
  stripe_fee_cents: number;
  margin_cents: number;
  margin_pct: number | null;
  cost_source: "actual" | "estimate";
  below_floor: boolean;
};

export type MarginReport = {
  days: number;
  floor_pct: number;
  pay_mode: string;
  hourly_cents: number;
  minutes_per_stop: number;
  totals: {
    stops: number;
    routes: number;
    revenue_cents: number;
    driver_cost_cents: number;
    stripe_fee_cents: number;
    margin_cents: number;
    margin_pct: number | null;
    stops_below_floor: number;
    routes_below_floor: number;
    estimated_share: number;
  };
  routes: MarginRow[];
  stops: MarginRow[];
};

export type TaxReport = {
  period_start: string;
  period_end: string;
  basis: string;
  registration_number: string;
  invoice_count: number;
  provinces: Array<{
    province: string;
    name: string;
    label: string;
    rate_pct: number;
    taxable_sales_cents: number;
    tax_cents: number;
    gst_hst_cents: number;
    qst_cents: number;
    lines: number;
  }>;
  gst34: {
    line_101_sales_cents: number;
    line_103_tax_collected_cents: number;
    line_106_itc_cents: number;
    line_109_net_tax_cents: number;
  };
  qst_collected_cents: number;
  notes: string[];
};

export type PayoutRunLine = {
  driver_id: string;
  name: string;
  email: string;
  deliveries: number;
  earned_cents: number;
  wallet_cents: number;
  amount_cents: number;
  payout_id: string | null;
  error?: string;
};

export type PayoutRun = {
  id: string;
  period_start: string;
  period_end: string;
  status: "draft" | "approved" | "paid" | "discarded";
  total_cents: number;
  driver_count: number;
  lines: PayoutRunLine[];
  approved_at: string | null;
  paid_at: string | null;
  created_at: string;
};

function period(start?: string, end?: string): string {
  const p = new URLSearchParams();
  if (start) p.set("start", start);
  if (end) p.set("end", end);
  const q = p.toString();
  return q ? `?${q}` : "";
}

export const financeOpsApi = {
  cash: (token: string) => adminFetch<CashBoard>(`${B}/cash`, token),
  reminders: (token: string) => adminFetch<{ items: ReminderDraft[] }>(`${B}/reminders`, token),
  queueReminders: (token: string) =>
    adminFetch<{ created: number; updated: number }>(`${B}/reminders/queue`, token, {
      method: "POST",
    }),
  approveReminders: (token: string, ids: string[]) =>
    adminFetch<{ decided: number; emails_sent: number; errors: string[] }>(
      `${B}/reminders/approve`,
      token,
      {
        method: "POST",
        body: JSON.stringify({ ids }),
      }
    ),
  discardReminders: (token: string, ids: string[]) =>
    adminFetch<{ decided: number }>(`${B}/reminders/discard`, token, {
      method: "POST",
      body: JSON.stringify({ ids }),
    }),
  stripe: (token: string) => adminFetch<StripeOverview>(`${B}/stripe`, token),
  margin: (token: string, days: number) =>
    adminFetch<MarginReport>(`${B}/margin?days=${days}`, token),
  taxReport: (token: string, start?: string, end?: string) =>
    adminFetch<TaxReport>(`${B}/tax-report${period(start, end)}`, token),
  downloadExport: (
    token: string,
    kind: "hst" | "quickbooks" | "xero",
    start?: string,
    end?: string
  ) =>
    downloadOrderFile(
      token,
      `${B}/exports/${kind}.csv${period(start, end)}`,
      `porterchain-${kind}.csv`
    ),
  payoutRuns: (token: string) => adminFetch<{ items: PayoutRun[] }>(`${B}/payout-runs`, token),
  createPayoutRun: (token: string, period_start: string, period_end: string) =>
    adminFetch<PayoutRun>(`${B}/payout-runs`, token, {
      method: "POST",
      body: JSON.stringify({ period_start, period_end }),
    }),
  payoutRunAction: (token: string, id: string, action: "approve" | "mark-paid" | "discard") =>
    adminFetch<PayoutRun>(`${B}/payout-runs/${id}/${action}`, token, { method: "POST" }),
  downloadBankCsv: (token: string, id: string) =>
    downloadOrderFile(token, `${B}/payout-runs/${id}/bank.csv`, "driver-payouts.csv"),
};

/** Quarter presets for GST/HST filing (calendar quarters). */
export function quarterRange(
  offset = 0,
  now = new Date()
): { start: string; end: string; label: string } {
  const q = Math.floor(now.getMonth() / 3) + offset;
  const year = now.getFullYear() + Math.floor(q / 4);
  const qi = ((q % 4) + 4) % 4;
  const start = new Date(Date.UTC(year, qi * 3, 1));
  const end = new Date(Date.UTC(year, qi * 3 + 3, 0));
  const iso = (d: Date) => d.toISOString().slice(0, 10);
  return { start: iso(start), end: iso(end), label: `Q${qi + 1} ${year}` };
}
