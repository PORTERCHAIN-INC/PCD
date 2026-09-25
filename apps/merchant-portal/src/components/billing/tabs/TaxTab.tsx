"use client";

import { type BillingOverview } from "@/lib/billing";
import { formatCents } from "@/lib/utils";
import { Kpi } from "./shared";

export function TaxTab({ overview }: { overview: BillingOverview }) {
  const tax = overview.tax_summary;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <Kpi label="Subtotal" value={formatCents(tax.subtotal_cents, tax.currency.toUpperCase())} />
      <Kpi label="Tax (HST/GST)" value={formatCents(tax.tax_cents, tax.currency.toUpperCase())} />
      <Kpi label="Fees" value={formatCents(tax.fees_cents, tax.currency.toUpperCase())} />
      <Kpi
        label="Total invoiced"
        value={formatCents(tax.total_cents, tax.currency.toUpperCase())}
      />
    </div>
  );
}
