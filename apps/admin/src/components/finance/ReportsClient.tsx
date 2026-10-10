"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { cn, formatCents } from "@porterchain/ui/utils";
import { PageSkeleton, TableSkeleton } from "@porterchain/ui/loading";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { exportGlCsv, financeApi } from "@/lib/finance";
import { financeOpsApi, quarterRange, type MarginRow } from "@/lib/finance-ops";
import {
  Empty,
  FinanceShell,
  Hero,
  PrimaryButton,
  QuietButton,
  Section,
  Stat,
} from "./FinanceShell";

const pct = (v: number | null) => (v == null ? "—" : `${v.toFixed(1)}%`);

function MarginList({
  rows,
  floor,
  kind,
}: {
  rows: MarginRow[];
  floor: number;
  kind: "route" | "stop";
}) {
  if (!rows.length) return <Empty>No delivered {kind}s in this window.</Empty>;
  return (
    <ul className="divide-y divide-primary/10">
      {rows.slice(0, 12).map((r) => (
        <li
          key={r.route_id ?? r.order_id}
          className="flex flex-wrap items-center gap-x-4 gap-y-1 py-3"
        >
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-primary">
              {kind === "route"
                ? `${r.day} · ${r.stops} stop${r.stops === 1 ? "" : "s"}`
                : (r.order_number ?? r.order_id)}
            </p>
            <p className="text-xs text-muted">
              {formatCents(r.revenue_cents)} revenue − {formatCents(r.driver_cost_cents)} driver
              {r.stripe_fee_cents ? ` − ${formatCents(r.stripe_fee_cents)} Stripe` : ""} ·{" "}
              {r.cost_source === "actual" ? "actual pay" : "estimated pay"}
            </p>
          </div>
          <span
            className={cn(
              "w-20 rounded-full px-2.5 py-1 text-center text-xs font-bold tabular-nums",
              r.below_floor ? "bg-red-700 text-white" : "bg-emerald-50 text-emerald-800"
            )}
            title={r.below_floor ? `Under the ${floor}% floor` : undefined}
          >
            {pct(r.margin_pct)}
          </span>
          <span className="w-24 text-right font-bold tabular-nums text-primary">
            {formatCents(r.margin_cents)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function ReportsClient() {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [days, setDays] = useState(30);
  const [q, setQ] = useState(() => quarterRange(0));
  const [view, setView] = useState<"route" | "stop">("route");

  const margin = useQuery({
    queryKey: ["finance-margin", days],
    enabled,
    queryFn: async () => financeOpsApi.margin(await getApiToken(), days),
  });
  const tax = useQuery({
    queryKey: ["finance-tax", q.start, q.end],
    enabled,
    queryFn: async () => financeOpsApi.taxReport(await getApiToken(), q.start, q.end),
  });
  const ledger = useQuery({
    queryKey: ["finance-ledger"],
    enabled,
    queryFn: async () => financeApi.ledger(await getApiToken()),
  });

  const download = async (kind: "hst" | "quickbooks" | "xero") =>
    financeOpsApi.downloadExport(await getApiToken(), kind, q.start, q.end);
  const m = margin.data;
  const t = tax.data;

  return (
    <FinanceShell
      title="Reports"
      subtitle="Margin per stop and route, GST/HST for filing, and exports for your accountant."
      primary={
        <PrimaryButton onClick={() => void download("hst")}>
          Download {q.label} GST/HST
        </PrimaryButton>
      }
    >
      {!m ? (
        <PageSkeleton rows={3} />
      ) : (
        <Hero label={`Margin · last ${days} days`} value={pct(m.totals.margin_pct)}>
          <div className="grid grid-cols-2 gap-6 border-t border-primary/10 pt-5 sm:grid-cols-4">
            <Stat label="Revenue (pre-tax)" value={formatCents(m.totals.revenue_cents)} />
            <Stat label="Driver cost" value={formatCents(m.totals.driver_cost_cents)} />
            <Stat
              label="Margin"
              value={formatCents(m.totals.margin_cents)}
              tone={m.totals.margin_cents < 0 ? "bad" : "good"}
            />
            <Stat
              label={`Under ${m.floor_pct}% floor`}
              value={`${m.totals.routes_below_floor} routes · ${m.totals.stops_below_floor} stops`}
              tone={m.totals.routes_below_floor ? "bad" : "good"}
            />
          </div>
          <p className="mt-4 text-xs text-muted">
            Driver cost = actual pay credited; otherwise the {m.pay_mode.replace("_", " ")} pay plan
            at {formatCents(m.hourly_cents)}/h × {m.minutes_per_stop} min per stop (
            {Math.round(m.totals.estimated_share * 100)}% estimated).
          </p>
        </Hero>
      )}

      <Section
        title="Thinnest first"
        aside={
          <div className="flex flex-wrap gap-1">
            {(["route", "stop"] as const).map((v) => (
              <QuietButton key={v} onClick={() => setView(v)}>
                <span className={view === v ? "underline underline-offset-4" : ""}>
                  {v === "route" ? "Routes" : "Stops"}
                </span>
              </QuietButton>
            ))}
            <select
              aria-label="Window"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="min-h-10 rounded-xl border border-primary/15 bg-white px-2 text-sm"
            >
              {[7, 30, 90].map((d) => (
                <option key={d} value={d}>
                  {d} days
                </option>
              ))}
            </select>
          </div>
        }
      >
        {!m ? (
          <TableSkeleton rows={4} />
        ) : (
          <MarginList
            rows={view === "route" ? m.routes : m.stops}
            floor={m.floor_pct}
            kind={view}
          />
        )}
      </Section>

      <Section
        title={`GST/HST · ${q.label}`}
        aside={
          <div className="flex gap-1">
            <QuietButton onClick={() => setQ(quarterRange(-1))}>Last quarter</QuietButton>
            <QuietButton onClick={() => setQ(quarterRange(0))}>This quarter</QuietButton>
          </div>
        }
      >
        {!t ? (
          <TableSkeleton rows={4} />
        ) : (
          <div className="space-y-6">
            <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              <Stat label="Line 101 · Sales" value={formatCents(t.gst34.line_101_sales_cents)} />
              <Stat
                label="Line 103 · Collected"
                value={formatCents(t.gst34.line_103_tax_collected_cents)}
              />
              <Stat label="Line 106 · ITCs" value="From receipts" />
              <Stat
                label="Line 109 · Net (before ITCs)"
                value={formatCents(t.gst34.line_109_net_tax_cents)}
              />
            </dl>
            {t.provinces.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-[32rem] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-muted">
                    <tr>
                      <th className="py-2 pr-3 font-semibold">Province</th>
                      <th className="py-2 pr-3 font-semibold">Tax</th>
                      <th className="py-2 pr-3 text-right font-semibold">Taxable sales</th>
                      <th className="py-2 text-right font-semibold">Tax</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-primary/10">
                    {t.provinces.map((p) => (
                      <tr key={p.province}>
                        <td className="py-3 pr-3 font-semibold text-primary">{p.name}</td>
                        <td className="py-3 pr-3 text-muted">{p.label}</td>
                        <td className="py-3 pr-3 text-right tabular-nums">
                          {formatCents(p.taxable_sales_cents)}
                        </td>
                        <td className="py-3 text-right font-bold tabular-nums text-primary">
                          {formatCents(p.tax_cents)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <Empty>No invoices issued in {q.label}.</Empty>
            )}
            <p className="text-xs text-muted">
              {t.registration_number
                ? `GST/HST # ${t.registration_number} · `
                : "Add the GST/HST number in Settings → Finance · "}
              {t.invoice_count} invoices · {t.basis}. {t.notes[0]}
            </p>
          </div>
        )}
      </Section>

      <Section title="Exports">
        <div className="flex flex-wrap gap-2">
          <QuietButton onClick={() => void download("quickbooks")}>
            QuickBooks Online (CSV)
          </QuietButton>
          <QuietButton onClick={() => void download("xero")}>Xero (CSV)</QuietButton>
          <QuietButton onClick={() => void download("hst")}>GST/HST detail (CSV)</QuietButton>
          <QuietButton
            onClick={async () => exportGlCsv(await financeApi.exportGl(await getApiToken()))}
          >
            General ledger (CSV)
          </QuietButton>
        </div>
        <p className="mt-3 text-xs text-muted">
          One row per invoice line for {q.label}, tax code by destination province.
        </p>
      </Section>

      <Section title="Ledger">
        {ledger.isLoading ? (
          <TableSkeleton rows={4} />
        ) : !(ledger.data ?? []).length ? (
          <Empty>Ledger is empty.</Empty>
        ) : (
          <ul className="divide-y divide-primary/10">
            {(ledger.data ?? []).slice(0, 25).map((e) => (
              <li
                key={String(e.id)}
                className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm"
              >
                <span className="font-mono text-xs text-primary">{String(e.kind)}</span>
                <span className="text-xs text-muted">
                  {String(e.status)} · {String(e.created_at).slice(0, 10)}
                </span>
                <span className="w-24 text-right font-semibold tabular-nums text-primary">
                  {e.amount_cents != null ? formatCents(Number(e.amount_cents)) : "—"}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>
    </FinanceShell>
  );
}
