"use client";

import { type BillingOverview } from "@/lib/billing";
import { formatCents, formatDate } from "@/lib/utils";

export function RemittanceCard({
  remittance,
}: {
  remittance: NonNullable<BillingOverview["remittance"]>;
}) {
  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="font-semibold text-primary">How to pay</h2>
      <p className="mt-2 text-sm text-muted">{remittance.instructions}</p>
      <dl className="mt-4 grid gap-3 sm:grid-cols-2 text-sm">
        <div>
          <dt className="text-muted">Pay to</dt>
          <dd className="font-medium text-primary">{remittance.payee}</dd>
        </div>
        <div>
          <dt className="text-muted">Memo / invoice numbers</dt>
          <dd className="font-mono text-xs text-primary">{remittance.memo}</dd>
        </div>
        <div>
          <dt className="text-muted">Remittance advice</dt>
          <dd className="text-primary">
            {remittance.advice_email || "Add a billing email in Settings"}
          </dd>
        </div>
        <div>
          <dt className="text-muted">Amount due now</dt>
          <dd className="font-medium text-primary">{formatCents(remittance.outstanding_cents)}</dd>
        </div>
        {remittance.credits_applied_cents > 0 && (
          <div>
            <dt className="text-muted">Credits already applied</dt>
            <dd className="text-primary">−{formatCents(remittance.credits_applied_cents)}</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
