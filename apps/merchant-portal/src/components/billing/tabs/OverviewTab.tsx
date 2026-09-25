"use client";

import { useState } from "react";
import Link from "next/link";
import Button from "@/components/ui/Button";
import { billingApi, formatCycle, formatTerms, type BillingOverview } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";
import { Kpi, StatusBadge } from "./shared";
import { RemittanceCard } from "./RemittanceCard";

export function OverviewTab({
  overview,
  orgId,
  getToken,
  onPaid,
}: {
  overview: BillingOverview;
  orgId?: string;
  getToken: () => Promise<string>;
  onPaid?: () => void;
}) {
  const cp = overview.contract_pricing;
  const [payingAll, setPayingAll] = useState(false);
  const [payNotice, setPayNotice] = useState<string | null>(null);
  const canPayAll = overview.outstanding_invoices_cents > 0;

  async function payAll() {
    setPayingAll(true);
    setPayNotice(null);
    try {
      const token = await getToken();
      const result = await billingApi.payOutstanding(token, orgId);
      if (result.pay_url) {
        window.location.href = result.pay_url;
        return;
      }
      if (result.paid) {
        setPayNotice("All open invoices paid.");
        onPaid?.();
      }
    } catch (e) {
      setPayNotice(e instanceof Error ? e.message : "Could not start payment");
    } finally {
      setPayingAll(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-muted">
          Outstanding = open invoices + uninvoiced deliveries − credits (same number as Admin).
        </p>
        {canPayAll && (
          <Button size="sm" disabled={payingAll} onClick={() => void payAll()}>
            {payingAll
              ? "Opening…"
              : `Pay all due (${formatCents(overview.outstanding_invoices_cents)})`}
          </Button>
        )}
      </div>
      {payNotice && <p className="text-sm text-muted">{payNotice}</p>}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Kpi label="Outstanding balance" value={formatCents(overview.outstanding_balance_cents)} />
        <Kpi
          label="Invoiced outstanding"
          value={formatCents(overview.outstanding_invoices_cents)}
        />
        <Kpi label="Uninvoiced orders" value={formatCents(overview.uninvoiced_orders_cents)} />
        {(overview.credit_notes_cents ?? 0) > 0 && (
          <Kpi label="Credit notes" value={`−${formatCents(overview.credit_notes_cents!)}`} />
        )}
        {(overview.overdue_cents ?? 0) > 0 && (
          <Kpi label="Overdue amount" value={formatCents(overview.overdue_cents!)} />
        )}
        <Kpi label="Period spend" value={formatCents(overview.monthly_spend_cents)} />
        <Kpi label="Invoices due" value={String(overview.invoices_due)} />
        <Kpi label="Overdue" value={String(overview.overdue_invoices)} />
        <Kpi label="Net terms" value={`${overview.net_terms_days} days`} />
        <Kpi
          label="Credit limit"
          value={
            overview.credit_limit_cents != null ? formatCents(overview.credit_limit_cents) : "—"
          }
        />
        {overview.credit_limit_cents != null && overview.credit_limit_cents > 0 && (
          <Kpi
            label="Headroom"
            value={formatCents(overview.headroom_cents ?? overview.available_credit_cents ?? 0)}
          />
        )}
        <Kpi
          label="Credits applied"
          value={
            (overview.credits_applied_cents ?? overview.credit_notes_cents ?? 0) > 0
              ? `−${formatCents(overview.credits_applied_cents ?? overview.credit_notes_cents ?? 0)}`
              : formatCents(0)
          }
        />
        <Kpi
          label="Tax (period)"
          value={formatCents(
            overview.tax_summary.tax_cents,
            overview.tax_summary.currency.toUpperCase()
          )}
        />
        <Kpi
          label="Invoiced total (period)"
          value={formatCents(
            overview.tax_summary.total_cents,
            overview.tax_summary.currency.toUpperCase()
          )}
        />
      </div>

      {overview.remittance && <RemittanceCard remittance={overview.remittance} />}

      {overview.glossary && overview.glossary.length > 0 && (
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h2 className="font-semibold text-primary">Billing words</h2>
          <dl className="mt-3 grid gap-3 sm:grid-cols-2">
            {overview.glossary.map((row) => (
              <div key={row.term}>
                <dt className="text-sm font-medium text-primary">{row.term}</dt>
                <dd className="mt-0.5 text-sm text-muted">{row.meaning}</dd>
              </div>
            ))}
          </dl>
        </section>
      )}

      {overview.period_start && (
        <p className="text-sm text-muted">
          Current billing period: {formatDate(overview.period_start)} —{" "}
          {formatDate(overview.period_end || "")}
        </p>
      )}

      {cp.has_contract && (
        <section className="rounded-2xl border border-primary/10 bg-white p-5">
          <h2 className="font-semibold text-primary">Contract pricing</h2>
          <p className="mt-1 text-sm">
            {cp.contract_name} · Min commitment {formatCents(cp.minimum_monthly_commitment_cents)}
          </p>
          {cp.effective_from && (
            <p className="text-xs text-muted">
              Effective {formatDate(cp.effective_from)}
              {cp.effective_to ? ` — ${formatDate(cp.effective_to)}` : ""}
            </p>
          )}
        </section>
      )}
    </div>
  );
}
