"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PageSkeleton, TableSkeleton } from "@porterchain/ui/loading";
import { ListPager } from "@/components/crm/ListPager";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { financeApi } from "@/lib/finance";
import { financeOpsApi } from "@/lib/finance-ops";
import { Empty, FinanceShell, Hero, Section, Stat } from "./FinanceShell";

const FinancePaymentsGrid = dynamic(() => import("@/components/finance/FinancePaymentsGrid"), {
  ssr: false,
  loading: () => <TableSkeleton rows={6} />,
});

const date = (v: string | null) => (v ? String(v).slice(0, 10) : "—");

export default function PaymentsClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [offset, setOffset] = useState(0);

  const dash = useQuery({
    queryKey: ["finance-dashboard"],
    enabled,
    queryFn: async () => financeApi.dashboard(await getApiToken()),
  });
  const stripe = useQuery({
    queryKey: ["finance-stripe"],
    enabled,
    queryFn: async () => financeOpsApi.stripe(await getApiToken()),
  });
  const payments = useQuery({
    queryKey: ["finance-payments", offset],
    enabled,
    queryFn: async () => financeApi.payments(await getApiToken(), undefined, { limit: 50, offset }),
  });

  const s = stripe.data;
  return (
    <FinanceShell
      title="Payments"
      subtitle="Card payments (Stripe), Interac e-Transfers, refunds, disputes and bank payouts."
    >
      {dash.data ? (
        <Hero label="Collected this month" value={formatCents(dash.data.month_revenue_cents)}>
          <div className="grid grid-cols-2 gap-6 border-t border-primary/10 pt-5 sm:grid-cols-4">
            <Stat label="Success rate" value={`${dash.data.payment_success_rate}%`} />
            <Stat
              label="Stripe fees (recent payouts)"
              value={formatCents(s?.fees_cents_30d ?? 0)}
            />
            <Stat
              label="Open disputes"
              value={s ? `${s.open_disputes} · ${formatCents(s.open_dispute_cents)}` : "—"}
              tone={s?.open_disputes ? "bad" : undefined}
            />
            <Stat
              label="Unreconciled payouts"
              value={String(s?.unreconciled ?? 0)}
              tone={s?.unreconciled ? "bad" : "good"}
            />
          </div>
        </Hero>
      ) : (
        <PageSkeleton rows={2} />
      )}

      <Section title="Stripe payouts to the bank">
        {!s ? (
          <TableSkeleton rows={3} />
        ) : !s.payouts.length ? (
          <Empty>Payouts appear when Stripe sends payout webhooks (payout.paid).</Empty>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[40rem] text-left text-sm">
              <thead className="text-xs uppercase tracking-wide text-muted">
                <tr>
                  <th className="py-2 pr-3 font-semibold">Arrives</th>
                  <th className="py-2 pr-3 text-right font-semibold">Gross</th>
                  <th className="py-2 pr-3 text-right font-semibold">Fees</th>
                  <th className="py-2 pr-3 text-right font-semibold">Refunds</th>
                  <th className="py-2 pr-3 text-right font-semibold">Payout</th>
                  <th className="py-2 font-semibold">Match</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-primary/10">
                {s.payouts.map((p) => (
                  <tr key={p.id}>
                    <td className="py-3 pr-3 text-primary">{date(p.arrival_date)}</td>
                    <td className="py-3 pr-3 text-right tabular-nums">
                      {p.gross_cents != null ? formatCents(p.gross_cents) : "—"}
                    </td>
                    <td className="py-3 pr-3 text-right tabular-nums">
                      {p.fee_cents != null ? formatCents(p.fee_cents) : "—"}
                    </td>
                    <td className="py-3 pr-3 text-right tabular-nums">
                      {p.refund_cents ? formatCents(p.refund_cents) : "—"}
                    </td>
                    <td className="py-3 pr-3 text-right font-bold tabular-nums text-primary">
                      {formatCents(p.amount_cents)}
                    </td>
                    <td className="py-3">
                      <span
                        className={cn(
                          "rounded-full px-2.5 py-1 text-xs font-semibold",
                          p.reconciled
                            ? "bg-emerald-50 text-emerald-800"
                            : p.status === "paid"
                              ? "bg-red-50 text-red-800"
                              : "bg-primary/5 text-primary"
                        )}
                      >
                        {p.reconciled
                          ? "Reconciled"
                          : p.status === "paid"
                            ? `Off by ${formatCents(Math.abs(p.difference_cents ?? 0))}`
                            : p.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      <Section title="Disputes">
        {!s ? null : !s.disputes.length ? (
          <Empty>
            No disputes. Disputes opened in the Stripe dashboard show up here automatically.
          </Empty>
        ) : (
          <ul className="divide-y divide-primary/10">
            {s.disputes.map((d) => (
              <li key={d.id} className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3">
                <div className="min-w-0 flex-1">
                  <p className="font-semibold capitalize text-primary">
                    {(d.reason ?? "dispute").replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-muted">
                    {d.dispute_id}{" "}
                    {d.open && d.evidence_due_by ? `· evidence due ${date(d.evidence_due_by)}` : ""}
                    {d.invoice_id ? (
                      <>
                        {" · "}
                        <Link
                          className="text-secondary underline"
                          href={`/finance/invoices/${d.invoice_id}`}
                        >
                          invoice
                        </Link>
                      </>
                    ) : null}
                  </p>
                </div>
                <span
                  className={cn(
                    "rounded-full px-2.5 py-1 text-xs font-semibold",
                    d.open
                      ? "bg-red-50 text-red-800"
                      : d.status === "won"
                        ? "bg-emerald-50 text-emerald-800"
                        : "bg-primary/5 text-primary"
                  )}
                >
                  {d.status.replace(/_/g, " ")}
                </span>
                <span className="w-24 text-right font-bold tabular-nums text-primary">
                  {formatCents(d.amount_cents ?? 0)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="All payments">
        {payments.isLoading ? (
          <TableSkeleton rows={6} />
        ) : (
          <>
            <FinancePaymentsGrid rows={payments.data?.items ?? []} />
            <ListPager
              total={payments.data?.total ?? 0}
              limit={payments.data?.limit ?? 50}
              offset={offset}
              onPage={setOffset}
            />
          </>
        )}
      </Section>
    </FinanceShell>
  );
}
