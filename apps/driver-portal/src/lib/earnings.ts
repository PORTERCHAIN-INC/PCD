export interface EarningsLineItem {
  id: string;
  type: string;
  amount_cents: number;
  description: string;
  reference_id: string | null;
  created_at: string | null;
}

export interface DriverBonusRow {
  id: string;
  title: string;
  amount_cents: number;
  status: string;
  criteria: Record<string, unknown>;
  expires_at: string | null;
  created_at: string | null;
}

export interface PayoutRow {
  id: string;
  amount_cents: number;
  currency: string;
  status: string;
  reference: string | null;
  created_at: string | null;
}

export interface StatementRow {
  id: string;
  period_label: string;
  period_start: string;
  period_end: string;
  gross_cents: number;
  deductions_cents: number;
  net_cents: number;
  deliveries: number;
}

export interface TaxSummary {
  ytd_gross_cents: number;
  month_gross_cents: number;
  withheld_cents: number;
  estimated_tax_cents: number;
  tax_rate_percent: number;
  note: string;
}

export interface PaymentSchedule {
  frequency: string;
  day_of_week: string;
  cutoff_description: string;
  deposit_delay_business_days: number;
  currency: string;
  next_payout_date: string;
}

export interface DriverEarningsSnapshot {
  today_cents: number;
  week_cents: number;
  month_cents: number;
  completed_deliveries_today: number;
  completed_deliveries_week: number;
  completed_deliveries_month: number;
  wallet_balance_cents: number;
  bonuses: DriverBonusRow[];
  adjustments: EarningsLineItem[];
  incentives: EarningsLineItem[];
  deductions: EarningsLineItem[];
  payout_history: PayoutRow[];
  taxes: TaxSummary;
  payment_schedule: PaymentSchedule;
  last_updated: string;
}

export function statementDownloadUrl(statementId: string): string {
  return `/api/driver/v1/earnings/statements/${statementId}/download`;
}

export function formatEarningsDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
