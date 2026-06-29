"use client";

import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getBillingStatement, listInvoices } from "@/lib/api";
import { formatCents, formatDate } from "@/lib/utils";
import { useEffect, useState } from "react";

export default function BillingPage() {
  const { getApiToken, orgId, isSignedIn, isLoaded } = useMerchantAuth();
  const [statement, setStatement] = useState<Awaited<
    ReturnType<typeof getBillingStatement>
  > | null>(null);
  const [invoices, setInvoices] = useState<Awaited<ReturnType<typeof listInvoices>>>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isLoaded || !isSignedIn) return;
    (async () => {
      try {
        const token = await getApiToken();
        const [stmt, inv] = await Promise.all([
          getBillingStatement(token, orgId),
          listInvoices(token, orgId),
        ]);
        setStatement(stmt);
        setInvoices(inv);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load billing");
      }
    })();
  }, [getApiToken, orgId, isLoaded, isSignedIn]);

  if (error) return <p className="text-red-600">{error}</p>;
  if (!statement) return <p className="text-muted">Loading…</p>;

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-primary">Billing</h1>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card label="Payment terms" value={statement.payment_terms.replace("_", " ")} />
        <Card
          label="Outstanding balance"
          value={formatCents(statement.outstanding_balance_cents)}
        />
        <Card label="Monthly orders" value={String(statement.monthly_orders)} />
        <Card label="Monthly spend" value={formatCents(statement.monthly_spend_cents)} />
      </div>

      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="text-lg font-semibold text-primary">Invoices</h2>
        {invoices.length === 0 ? (
          <p className="mt-4 text-sm text-muted">
            No invoices yet — Net terms orders appear here when invoiced.
          </p>
        ) : (
          <table className="mt-4 w-full text-left text-sm">
            <thead>
              <tr className="border-b border-primary/10 text-muted">
                <th className="py-2">Invoice</th>
                <th className="py-2">Amount</th>
                <th className="py-2">Date</th>
                <th className="py-2">PDF</th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.invoice_id} className="border-b border-primary/5">
                  <td className="py-3 font-mono text-xs">{inv.invoice_number}</td>
                  <td className="py-3">
                    {formatCents(inv.amount_cents, inv.currency.toUpperCase())}
                  </td>
                  <td className="py-3">{formatDate(inv.created_at)}</td>
                  <td className="py-3">
                    {inv.stripe_receipt_url ? (
                      <a
                        href={inv.stripe_receipt_url}
                        className="text-secondary hover:underline"
                        target="_blank"
                        rel="noreferrer"
                      >
                        Download
                      </a>
                    ) : (
                      "—"
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function Card({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-sm text-muted">{label}</p>
      <p className="mt-2 text-xl font-bold text-primary">{value}</p>
    </div>
  );
}
