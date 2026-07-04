"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  Calendar,
  Download,
  Gift,
  MinusCircle,
  RefreshCw,
  Sparkles,
  TrendingUp,
  Wallet,
} from "lucide-react";
import DriverShell from "@/components/DriverShell";
import { useDriverEarnings } from "@/hooks/useDriverEarnings";
import { hasDriverSession } from "@/lib/api";
import { formatEarningsDate, statementDownloadUrl, type EarningsLineItem } from "@/lib/earnings";
import { cn, formatCents } from "@/lib/utils";

export default function EarningsPage() {
  const router = useRouter();
  const { data, statements, error, loading, refreshing, refresh } = useDriverEarnings();

  useEffect(() => {
    hasDriverSession().then((ok) => {
      if (!ok) router.replace("/login");
    });
  }, [router]);

  if (loading && !data) {
    return (
      <DriverShell>
        <div className="animate-pulse space-y-4">
          <div className="h-10 w-48 rounded-xl bg-white" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-28 rounded-2xl bg-white" />
            ))}
          </div>
        </div>
      </DriverShell>
    );
  }

  const snap = data!;

  return (
    <DriverShell>
      <header className="flex flex-col gap-3 border-b border-[var(--primary)]/8 pb-6 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold">Earnings</h1>
          <p className="mt-1 text-sm text-[var(--muted)]">
            Finance Engine totals — synced from Porterchain
          </p>
        </div>
        <button
          type="button"
          onClick={refresh}
          disabled={refreshing}
          className="inline-flex items-center gap-2 rounded-xl border border-[var(--primary)]/10 bg-white px-4 py-2 text-sm font-medium"
        >
          <RefreshCw className={cn("h-4 w-4", refreshing && "animate-spin")} />
          {refreshing ? "Syncing…" : "Sync now"}
        </button>
      </header>

      {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <section className="mt-6">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-[var(--muted)]">
          Period Summary
        </h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            label="Today's Earnings"
            value={formatCents(snap.today_cents)}
            icon={TrendingUp}
            accent
          />
          <KpiCard label="Weekly Earnings" value={formatCents(snap.week_cents)} icon={Calendar} />
          <KpiCard label="Monthly Earnings" value={formatCents(snap.month_cents)} icon={Wallet} />
          <KpiCard
            label="Completed Deliveries"
            value={String(snap.completed_deliveries_today)}
            hint={`${snap.completed_deliveries_week} this week · ${snap.completed_deliveries_month} this month`}
            icon={ArrowUpCircle}
          />
        </div>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <LineItemsCard title="Bonuses" icon={Gift} empty="No bonuses on file">
          {snap.bonuses.map((b) => (
            <li
              key={b.id}
              className="flex justify-between gap-4 rounded-xl bg-[var(--gray-bg)] px-3 py-2 text-sm"
            >
              <div>
                <p className="font-medium">{b.title}</p>
                <p className="text-xs capitalize text-[var(--muted)]">{b.status}</p>
              </div>
              <span className="font-semibold text-emerald-700">{formatCents(b.amount_cents)}</span>
            </li>
          ))}
        </LineItemsCard>
        <LineItemsCard title="Adjustments" icon={Sparkles} empty="No adjustments">
          {snap.adjustments.map((row) => (
            <TransactionRow key={row.id} row={row} />
          ))}
        </LineItemsCard>
        <LineItemsCard title="Incentives" icon={ArrowUpCircle} empty="No incentives">
          {snap.incentives.map((row) => (
            <TransactionRow key={row.id} row={row} />
          ))}
        </LineItemsCard>
        <LineItemsCard title="Deductions" icon={MinusCircle} empty="No deductions">
          {snap.deductions.map((row) => (
            <TransactionRow key={row.id} row={row} negative />
          ))}
        </LineItemsCard>
      </section>

      <section className="mt-8 grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <Calendar className="h-5 w-5 text-[var(--secondary)]" />
            <h2 className="text-lg font-bold">Payment Schedule</h2>
          </div>
          <dl className="mt-4 space-y-2 text-sm">
            <Row label="Frequency" value={snap.payment_schedule.frequency} />
            <Row label="Payout day" value={snap.payment_schedule.day_of_week} />
            <Row label="Cutoff" value={snap.payment_schedule.cutoff_description} />
            <Row
              label="Next payout"
              value={formatEarningsDate(snap.payment_schedule.next_payout_date)}
            />
            <Row
              label="Deposit delay"
              value={`${snap.payment_schedule.deposit_delay_business_days} business days`}
            />
          </dl>
        </div>
        <div className="rounded-2xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-2">
            <ArrowDownCircle className="h-5 w-5 text-[var(--secondary)]" />
            <h2 className="text-lg font-bold">Taxes</h2>
          </div>
          <dl className="mt-4 space-y-2 text-sm">
            <Row label="YTD gross" value={formatCents(snap.taxes.ytd_gross_cents)} />
            <Row label="Month gross" value={formatCents(snap.taxes.month_gross_cents)} />
            <Row label="Withheld" value={formatCents(snap.taxes.withheld_cents)} />
            <Row
              label="Estimated tax"
              value={formatCents(snap.taxes.estimated_tax_cents)}
              hint={`${snap.taxes.tax_rate_percent}% planning rate`}
            />
          </dl>
          <p className="mt-4 text-xs text-[var(--muted)]">{snap.taxes.note}</p>
        </div>
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Statements</h2>
        <p className="mt-1 text-sm text-[var(--muted)]">
          Monthly earnings statements from Finance Engine
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-[var(--primary)]/10 text-[var(--muted)]">
                <th className="pb-2 font-medium">Period</th>
                <th className="pb-2 font-medium">Gross</th>
                <th className="pb-2 font-medium">Deductions</th>
                <th className="pb-2 font-medium">Net</th>
                <th className="pb-2 font-medium">Deliveries</th>
                <th className="pb-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {statements.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-6 text-[var(--muted)]">
                    No statements yet
                  </td>
                </tr>
              ) : (
                statements.map((s) => (
                  <tr key={s.id} className="border-b border-[var(--primary)]/5">
                    <td className="py-3 font-medium">{s.period_label}</td>
                    <td className="py-3">{formatCents(s.gross_cents)}</td>
                    <td className="py-3">{formatCents(s.deductions_cents)}</td>
                    <td className="py-3 font-semibold">{formatCents(s.net_cents)}</td>
                    <td className="py-3">{s.deliveries}</td>
                    <td className="py-3 text-right">
                      <a
                        href={statementDownloadUrl(s.id)}
                        className="inline-flex items-center gap-1 rounded-lg border border-[var(--primary)]/10 px-3 py-1.5 text-xs font-semibold hover:bg-[var(--gray-bg)]"
                      >
                        <Download className="h-3.5 w-3.5" />
                        Download
                      </a>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <section className="mt-8 rounded-2xl bg-white p-5 shadow-sm">
        <h2 className="text-lg font-bold">Payout History</h2>
        <ul className="mt-4 space-y-2">
          {snap.payout_history.length === 0 ? (
            <li className="text-sm text-[var(--muted)]">No payouts recorded</li>
          ) : (
            snap.payout_history.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between gap-4 rounded-xl bg-[var(--gray-bg)] px-4 py-3 text-sm"
              >
                <div>
                  <p className="font-medium">{formatCents(p.amount_cents)}</p>
                  <p className="text-xs text-[var(--muted)]">
                    {formatEarningsDate(p.created_at)} · {p.reference || "Payout"}
                  </p>
                </div>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs font-semibold capitalize">
                  {p.status}
                </span>
              </li>
            ))
          )}
        </ul>
      </section>

      <p className="mt-6 text-xs text-[var(--muted)]">
        Last synced {new Date(snap.last_updated).toLocaleString()}
      </p>
    </DriverShell>
  );
}

function KpiCard({
  label,
  value,
  hint,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  hint?: string;
  icon: React.ComponentType<{ className?: string }>;
  accent?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl p-5 shadow-sm",
        accent ? "bg-[var(--primary)] text-white" : "bg-white"
      )}
    >
      <div className="flex items-center gap-2">
        <Icon className={cn("h-4 w-4", accent ? "text-white/80" : "text-[var(--secondary)]")} />
        <p className={cn("text-sm", accent ? "text-white/80" : "text-[var(--muted)]")}>{label}</p>
      </div>
      <p className="mt-2 text-2xl font-bold">{value}</p>
      {hint && (
        <p className={cn("mt-1 text-xs", accent ? "text-white/70" : "text-[var(--muted)]")}>
          {hint}
        </p>
      )}
    </div>
  );
}

function LineItemsCard({
  title,
  icon: Icon,
  empty,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  empty: string;
  children: React.ReactNode;
}) {
  const items = Array.isArray(children) ? children : [children];
  const hasItems = items.some((c) => c != null);
  return (
    <div className="rounded-2xl bg-white p-5 shadow-sm">
      <div className="flex items-center gap-2">
        <Icon className="h-5 w-5 text-[var(--secondary)]" />
        <h2 className="text-lg font-bold">{title}</h2>
      </div>
      <ul className="mt-4 space-y-2">
        {!hasItems ? <li className="text-sm text-[var(--muted)]">{empty}</li> : children}
      </ul>
    </div>
  );
}

function TransactionRow({ row, negative }: { row: EarningsLineItem; negative?: boolean }) {
  return (
    <li className="flex justify-between gap-4 rounded-xl bg-[var(--gray-bg)] px-3 py-2 text-sm">
      <div>
        <p className="font-medium">{row.description || row.type}</p>
        <p className="text-xs text-[var(--muted)]">{formatEarningsDate(row.created_at)}</p>
      </div>
      <span className={cn("font-semibold", negative ? "text-red-700" : "text-emerald-700")}>
        {negative ? "−" : "+"}
        {formatCents(row.amount_cents)}
      </span>
    </li>
  );
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-[var(--muted)]">{label}</dt>
      <dd className="text-right font-semibold capitalize">
        {value}
        {hint && (
          <span className="mt-0.5 block text-xs font-normal text-[var(--muted)]">{hint}</span>
        )}
      </dd>
    </div>
  );
}
