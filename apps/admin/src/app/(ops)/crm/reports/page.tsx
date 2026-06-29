"use client";

import { useApiData } from "@/hooks/useApiData";
import { crm } from "@/lib/crm";
import { SectionCard, Spinner } from "@/components/crm/primitives";
import { STAGE_ACCENT, STAGE_LABELS, money, titleCase } from "@/lib/crmFormat";

function Kpi({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <p className="text-xs font-medium text-muted">{label}</p>
      <p className="mt-2 text-2xl font-bold text-primary">{value}</p>
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export default function ReportsPage() {
  const { data, error } = useApiData((t) => crm.reports(t));

  if (error) return <p className="text-red-600">{error}</p>;
  if (!data) return <Spinner label="Loading reports…" />;

  const maxStage = Math.max(1, ...data.pipeline.map((s) => s.value_cents));
  const maxRep = Math.max(1, ...data.sales_performance.map((r) => r.revenue_cents));

  return (
    <div className="space-y-6">
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <Kpi
          label="Conversion Rate"
          value={`${data.conversion_rate_percent}%`}
          hint="Won / closed deals"
        />
        <Kpi
          label="Revenue Forecast"
          value={money(data.revenue_forecast_cents)}
          hint="Probability-weighted"
        />
        <Kpi label="Quote Win Rate" value={`${data.quote_win_rate_percent}%`} />
        <Kpi label="Avg Time to Close" value={`${data.avg_time_to_close_days}d`} />
        <Kpi label="Merchant Acq. Cost" value={money(data.merchant_acquisition_cost_cents)} />
      </div>

      <SectionCard title="Sales pipeline">
        <div className="space-y-3 p-5">
          {data.pipeline.map((s) => (
            <div key={s.stage}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="font-medium text-primary">
                  {STAGE_LABELS[s.stage] ?? titleCase(s.stage)}{" "}
                  <span className="text-muted">· {s.count}</span>
                </span>
                <span className="font-semibold text-primary">{money(s.value_cents)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                <div
                  className="h-full rounded-full"
                  style={{
                    width: `${(s.value_cents / maxStage) * 100}%`,
                    background: STAGE_ACCENT[s.stage] ?? "#2563eb",
                  }}
                />
              </div>
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-6 lg:grid-cols-2">
        <SectionCard title="Sales performance">
          <div className="space-y-3 p-5">
            {data.sales_performance.length === 0 && (
              <p className="text-sm text-muted">No deal owners yet.</p>
            )}
            {data.sales_performance.map((rep) => (
              <div key={rep.owner_id}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="text-primary">
                    {rep.owner_id === "unassigned" ? "Unassigned" : rep.owner_id.slice(0, 8)}{" "}
                    <span className="text-muted">· {rep.deals} deals</span>
                  </span>
                  <span className="font-semibold text-primary">{money(rep.revenue_cents)}</span>
                </div>
                <div className="h-2 overflow-hidden rounded-full bg-gray-bg">
                  <div
                    className="h-full rounded-full bg-secondary"
                    style={{ width: `${(rep.revenue_cents / maxRep) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard title="Lead sources">
          <div className="divide-y divide-primary/5">
            {data.lead_sources.length === 0 && (
              <p className="px-5 py-8 text-center text-sm text-muted">No leads yet.</p>
            )}
            {data.lead_sources.map((s) => (
              <div key={s.source} className="flex items-center justify-between px-5 py-3 text-sm">
                <span className="text-primary">{titleCase(s.source)}</span>
                <span className="font-semibold text-primary">{s.count}</span>
              </div>
            ))}
          </div>
        </SectionCard>
      </div>
    </div>
  );
}
