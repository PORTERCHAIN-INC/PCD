"use client";

import { type BillingOverview } from "@/lib/billing";
import { formatCents } from "@/lib/utils";

/** "Oct 1"; period ends are exclusive, so show the day before. */
function dayLabel(iso: string, exclusiveEnd = false) {
  if (!iso) return "";
  const d = new Date(iso);
  if (exclusiveEnd) d.setTime(d.getTime() - 1000);
  return d.toLocaleDateString("en-CA", { month: "short", day: "numeric", year: "numeric" });
}
import { RemittanceCard } from "./RemittanceCard";

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="py-4 sm:px-6 sm:py-0 first:sm:pl-0">
      <p className="text-xs font-semibold uppercase tracking-[0.12em] text-muted">{label}</p>
      <p className="mt-1 text-2xl font-bold tabular-nums text-primary">{value}</p>
      {hint ? <p className="mt-0.5 text-xs text-muted">{hint}</p> : null}
    </div>
  );
}

/** One number first (what you owe), then how to pay it. Everything else is one tap away. */
export function OverviewTab({ overview }: { overview: BillingOverview }) {
  const cp = overview.contract_pricing;
  const overdue = overview.overdue_cents ?? 0;
  const credit = overview.credit_balance_cents ?? 0;

  return (
    <div className="space-y-8">
      <section
        className="rounded-3xl border border-primary/10 bg-white p-6 sm:p-8"
        aria-labelledby="balance"
      >
        <p id="balance" className="text-xs font-semibold uppercase tracking-[0.14em] text-muted">
          Balance due
        </p>
        <p className="mt-2 text-5xl font-extrabold tracking-tight tabular-nums text-primary sm:text-6xl">
          {formatCents(overview.outstanding_balance_cents)}
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
          {overdue > 0 ? (
            <span className="rounded-full bg-red-50 px-3 py-1 font-semibold text-red-800">
              {formatCents(overdue)} past due
            </span>
          ) : (
            <span className="rounded-full bg-emerald-50 px-3 py-1 font-semibold text-emerald-800">
              Nothing past due
            </span>
          )}
          {credit > 0 ? (
            <span className="text-primary">
              {formatCents(credit)} credit applies to your next invoice
            </span>
          ) : null}
          <span className="text-muted">Net {overview.net_terms_days} days</span>
        </div>
        <div className="mt-8 grid divide-y divide-primary/10 border-t border-primary/10 pt-6 sm:grid-cols-3 sm:divide-x sm:divide-y-0">
          <Stat
            label="Invoiced"
            value={formatCents(overview.outstanding_invoices_cents)}
            hint="open invoices"
          />
          <Stat
            label="Not invoiced yet"
            value={formatCents(overview.uninvoiced_orders_cents)}
            hint="on your next cycle invoice"
          />
          <Stat
            label="This period"
            value={formatCents(overview.monthly_spend_cents)}
            hint={`${overview.monthly_orders} deliveries`}
          />
        </div>
      </section>

      {overview.remittance ? <RemittanceCard remittance={overview.remittance} /> : null}

      <dl className="grid gap-x-8 gap-y-3 text-sm sm:grid-cols-2">
        {overview.period_start ? (
          <div className="flex justify-between gap-4 border-b border-primary/10 pb-3">
            <dt className="text-muted">Current period</dt>
            <dd className="text-right font-medium text-primary">
              {dayLabel(overview.period_start)} – {dayLabel(overview.period_end || "", true)}
            </dd>
          </div>
        ) : null}
        <div className="flex justify-between gap-4 border-b border-primary/10 pb-3">
          <dt className="text-muted">Credit limit</dt>
          <dd className="text-right font-medium tabular-nums text-primary">
            {overview.credit_limit_cents ? formatCents(overview.credit_limit_cents) : "—"}
            {overview.credit_limit_cents && overview.headroom_cents != null
              ? ` · ${formatCents(overview.headroom_cents)} left`
              : ""}
          </dd>
        </div>
        <div className="flex justify-between gap-4 border-b border-primary/10 pb-3">
          <dt className="text-muted">Tax this period</dt>
          <dd className="text-right font-medium tabular-nums text-primary">
            {formatCents(
              overview.tax_summary.tax_cents,
              overview.tax_summary.currency.toUpperCase()
            )}
          </dd>
        </div>
        {cp.has_contract ? (
          <div className="flex justify-between gap-4 border-b border-primary/10 pb-3">
            <dt className="text-muted">Contract</dt>
            <dd className="text-right font-medium text-primary">
              {cp.contract_name}
              {cp.minimum_monthly_commitment_cents
                ? ` · min ${formatCents(cp.minimum_monthly_commitment_cents)}/mo`
                : ""}
            </dd>
          </div>
        ) : null}
      </dl>
    </div>
  );
}
